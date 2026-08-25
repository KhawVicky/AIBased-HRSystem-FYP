"""Lazy model/tokenizer loading shared by the local API and RunPod worker."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self.model: Any | None = None
        self.tokenizer: Any | None = None
        self.loaded = False

    def load(self) -> None:
        started = time.perf_counter()
        if self.config.mock_llm:
            self.loaded = True
            logger.info("mock model ready duration_ms=%d", int((time.perf_counter() - started) * 1000))
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name, token=self.config.hf_token)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.padding_side = "left"

            kwargs: dict[str, Any] = {
                "token": self.config.hf_token,
                "torch_dtype": torch.float16 if self.config.device == "cuda" else torch.float32,
            }
            if self.config.device == "cuda" and torch.cuda.is_available():
                kwargs["device_map"] = "auto"
                kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
            self.model = AutoModelForCausalLM.from_pretrained(self.config.model_name, **kwargs)
            self.model.eval()
            self.loaded = True
            logger.info("model ready duration_ms=%d", int((time.perf_counter() - started) * 1000))
        except Exception:
            logger.exception("model load failed")
            self.loaded = False

    def generate(self, messages: list[dict[str, str]]) -> str:
        if not self.loaded:
            raise RuntimeError("Model is not ready")
        if self.config.mock_llm:
            return json.dumps({"criteria": [{"type": "relevant_skill", "name": "Mock Job Capability", "sourceText": "mock"}]})
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if self.config.device == "cuda":
            inputs = {key: value.to(self.model.device) for key, value in inputs.items()}
        output = self.model.generate(**inputs, max_new_tokens=self.config.max_new_tokens, do_sample=False)
        return self.tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
