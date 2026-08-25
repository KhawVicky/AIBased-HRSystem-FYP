// Shows the candidate question step.
import { useState } from "react";
import { GripVertical, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { ApplicationQuestion } from "../CreateJob";
import { Button } from "../../ui/button";
import { Card, CardContent } from "../../ui/card";
import { Checkbox } from "../../ui/checkbox";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../ui/select";

interface Step2ApplicationQuestionsProps {
  questions: ApplicationQuestion[];
  setQuestions: (questions: ApplicationQuestion[]) => void;
  onNext: () => void;
  onBack: () => void;
  isSaving?: boolean;
}

const fieldTypes: { value: ApplicationQuestion["fieldType"]; label: string }[] = [
  { value: "text", label: "Text" },
  { value: "textarea", label: "Long text" },
  { value: "number", label: "Number" },
  { value: "dropdown", label: "Dropdown" },
];

// Renders the Step2 Application Questions component.
export function Step2ApplicationQuestions({
  questions,
  setQuestions,
  onNext,
  onBack,
  isSaving = false,
}: Step2ApplicationQuestionsProps) {
  const [draggedQuestionId, setDraggedQuestionId] = useState<string | null>(null);
  const [dragOverQuestionId, setDragOverQuestionId] = useState<string | null>(null);

  // Adds question.
  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        id: `question-${Date.now()}`,
        question: "",
        fieldType: "text",
        required: false,
        options: [],
      },
    ]);
  };

  // Updates question.
  const updateQuestion = (
    id: string,
    updates: Partial<ApplicationQuestion>,
  ) => {
    setQuestions(
      questions.map((question) =>
        question.id === id ? { ...question, ...updates } : question,
      ),
    );
  };

  // Updates option.
  const updateOption = (questionId: string, index: number, value: string) => {
    const question = questions.find((item) => item.id === questionId);
    if (!question) return;
    updateQuestion(questionId, {
      options: question.options.map((option, optionIndex) =>
        optionIndex === index ? value : option,
      ),
    });
  };

  // Removes option.
  const removeOption = (questionId: string, index: number) => {
    const question = questions.find((item) => item.id === questionId);
    if (!question) return;
    updateQuestion(questionId, {
      options: question.options.filter((_, optionIndex) => optionIndex !== index),
    });
  };

  // Move the dragged question to the selected place.
  const moveQuestion = (targetQuestionId: string) => {
    if (!draggedQuestionId || draggedQuestionId === targetQuestionId) return;

    const fromIndex = questions.findIndex(
      (question) => question.id === draggedQuestionId,
    );
    const toIndex = questions.findIndex(
      (question) => question.id === targetQuestionId,
    );
    if (fromIndex < 0 || toIndex < 0) return;

    const reorderedQuestions = [...questions];
    const [movedQuestion] = reorderedQuestions.splice(fromIndex, 1);
    reorderedQuestions.splice(toIndex, 0, movedQuestion);
    setQuestions(reorderedQuestions);
  };

  // Clears drag state.
  const clearDragState = () => {
    setDraggedQuestionId(null);
    setDragOverQuestionId(null);
  };

  // Handles continue.
  const handleContinue = () => {
    // Dropdown questions need at least one filled option.
    const incompleteQuestion = questions.find(
      (question) =>
        !question.question.trim() ||
        (question.fieldType === "dropdown" &&
          !question.options.some((option) => option.trim())),
    );
    if (incompleteQuestion) {
      toast.error("Complete each question and its dropdown options");
      return;
    }
    onNext();
  };

  return (
    <div className="space-y-8">
      <Card className="border border-slate-200 shadow-sm">
        <CardContent className="p-8">
          <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="mb-2 text-xl font-semibold text-[#003B7A]">
                Candidate Questions
              </h2>
              <p className="text-sm text-slate-600">
                Choose what additional information candidates must provide for this job.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addQuestion}
              className="border-[#003B7A] text-[#003B7A] hover:bg-blue-50"
            >
              <Plus className="h-4 w-4" />
              Add question
            </Button>
          </div>

          {questions.length === 0 ? (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
              No additional questions. Candidates will complete the standard application fields.
            </div>
          ) : (
            <div className="space-y-4">
              {questions.map((question, index) => (
                <div
                  key={question.id}
                  onDragEnter={() => setDragOverQuestionId(question.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault();
                    moveQuestion(question.id);
                    clearDragState();
                  }}
                  className={`flex overflow-hidden rounded-md border border-slate-200 bg-white transition-colors ${
                    dragOverQuestionId === question.id &&
                    draggedQuestionId !== question.id
                      ? "border-blue-300 bg-blue-50/60"
                      : ""
                  }`}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    draggable
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = "move";
                      event.dataTransfer.setData("text/plain", question.id);
                      setDraggedQuestionId(question.id);
                    }}
                    onDragEnd={clearDragState}
                    aria-label={`Drag question ${index + 1} to reorder`}
                    title="Drag to reorder"
                    className="m-1 h-auto min-h-10 shrink-0 cursor-grab self-stretch text-slate-400 hover:bg-blue-50 hover:text-[#003B7A] active:cursor-grabbing"
                  >
                    <GripVertical className="h-5 w-5" />
                  </Button>
                  <div className="min-w-0 flex-1 p-4 pl-2">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-[#003B7A]">
                      Question {index + 1}
                    </h3>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        setQuestions(questions.filter((item) => item.id !== question.id))
                      }
                      aria-label={`Delete question ${index + 1}`}
                      title="Delete question"
                      className="text-slate-500 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="grid gap-3 md:grid-cols-[minmax(0,2fr)_minmax(180px,1fr)]">
                    <div className="space-y-2">
                      <Input
                        id={`question-${question.id}`}
                        value={question.question}
                        onChange={(event) =>
                          updateQuestion(question.id, { question: event.target.value })
                        }
                        placeholder="e.g. What is your expected salary?"
                        className="!h-10 min-h-10 bg-slate-50 px-4"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Answer field</Label>
                      <Select
                        value={question.fieldType}
                        onValueChange={(value) =>
                          updateQuestion(question.id, {
                            fieldType: value as ApplicationQuestion["fieldType"],
                            options: value === "dropdown" ? question.options : [],
                          })
                        }
                      >
                        <SelectTrigger className="!h-10 min-h-10 bg-slate-50 px-4">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {fieldTypes.map((fieldType) => (
                            <SelectItem key={fieldType.value} value={fieldType.value}>
                              {fieldType.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <label className="mt-3 flex w-fit cursor-pointer items-center gap-2 text-sm text-slate-700">
                    <Checkbox
                      checked={question.required}
                      onCheckedChange={(checked) =>
                        updateQuestion(question.id, { required: checked === true })
                      }
                    />
                    Required
                  </label>

                  {question.fieldType === "dropdown" && (
                    <div className="mt-4 space-y-3 border-l-2 border-blue-100 pl-4">
                      <div className="flex items-center justify-between gap-3">
                        <Label>Dropdown options</Label>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            updateQuestion(question.id, {
                              options: [...question.options, ""],
                            })
                          }
                        >
                          <Plus className="h-4 w-4" />
                          Add option
                        </Button>
                      </div>
                      {question.options.map((option, optionIndex) => (
                        <div key={optionIndex} className="flex items-center gap-2">
                          <Input
                            value={option}
                            onChange={(event) =>
                              updateOption(question.id, optionIndex, event.target.value)
                            }
                            placeholder={`Option ${optionIndex + 1}`}
                            className="!h-10 min-h-10 bg-slate-50"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => removeOption(question.id, optionIndex)}
                            aria-label={`Delete option ${optionIndex + 1}`}
                            title="Delete option"
                            className="shrink-0 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between pt-4">
        <Button type="button" variant="outline" onClick={onBack} disabled={isSaving}>
          Back
        </Button>
        <div className="flex gap-3">
          <Button
            type="button"
            onClick={handleContinue}
            disabled={isSaving}
            className="bg-[#003B7A] text-white hover:bg-[#002f63]"
          >
            Continue to Set Criteria
          </Button>
        </div>
      </div>
    </div>
  );
}
