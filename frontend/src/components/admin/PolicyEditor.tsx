import { useReducer, useEffect } from 'react';
import { ChevronDown, ChevronUp, Plus, Trash2 } from 'lucide-react';
import type { ExtractedLender, ExtractedProgram, ExtractedRule } from '../../types/policy-extraction';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

interface PolicyEditorProps {
  lender: ExtractedLender;
  programs: ExtractedProgram[];
  onUpdate: (lender: ExtractedLender, programs: ExtractedProgram[]) => void;
}

interface EditorState {
  editedLender: ExtractedLender;
  editedPrograms: ExtractedProgram[];
  expandedPrograms: Set<number>;
}

type EditorAction =
  | { type: 'INIT'; payload: { lender: ExtractedLender; programs: ExtractedProgram[] } }
  | { type: 'UPDATE_LENDER_FIELD'; payload: { field: keyof ExtractedLender; value: unknown } }
  | { type: 'UPDATE_PROGRAM_FIELD'; payload: { programIndex: number; field: keyof ExtractedProgram; value: unknown } }
  | { type: 'UPDATE_RULE'; payload: { programIndex: number; ruleIndex: number; rule: ExtractedRule } }
  | { type: 'DELETE_RULE'; payload: { programIndex: number; ruleIndex: number } }
  | { type: 'ADD_RULE'; payload: { programIndex: number } }
  | { type: 'DELETE_PROGRAM'; payload: { programIndex: number } }
  | { type: 'ADD_PROGRAM' }
  | { type: 'TOGGLE_PROGRAM'; payload: { programIndex: number } };

function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case 'INIT':
      return {
        editedLender: action.payload.lender,
        editedPrograms: action.payload.programs,
        expandedPrograms: new Set([0]),
      };
    case 'UPDATE_LENDER_FIELD':
      return {
        ...state,
        editedLender: { ...state.editedLender, [action.payload.field]: action.payload.value },
      };
    case 'UPDATE_PROGRAM_FIELD': {
      const updated = [...state.editedPrograms];
      updated[action.payload.programIndex] = {
        ...updated[action.payload.programIndex],
        [action.payload.field]: action.payload.value,
      };
      return {
        ...state,
        editedPrograms: updated,
      };
    }
    case 'UPDATE_RULE': {
      const updated = [...state.editedPrograms];
      const rules = [...(updated[action.payload.programIndex].rules || [])];
      rules[action.payload.ruleIndex] = action.payload.rule;
      updated[action.payload.programIndex] = { ...updated[action.payload.programIndex], rules };
      return {
        ...state,
        editedPrograms: updated,
      };
    }
    case 'DELETE_RULE': {
      const updated = [...state.editedPrograms];
      const rules = [...(updated[action.payload.programIndex].rules || [])];
      rules.splice(action.payload.ruleIndex, 1);
      updated[action.payload.programIndex] = { ...updated[action.payload.programIndex], rules };
      return {
        ...state,
        editedPrograms: updated,
      };
    }
    case 'ADD_RULE': {
      const updated = [...state.editedPrograms];
      const rules = [...(updated[action.payload.programIndex].rules || [])];
      rules.push({
        rule_type: 'min_fico',
        rule_name: 'New Rule',
        criteria: {},
        weight: 1.0,
        is_mandatory: true,
      });
      updated[action.payload.programIndex] = { ...updated[action.payload.programIndex], rules };
      return {
        ...state,
        editedPrograms: updated,
      };
    }
    case 'DELETE_PROGRAM':
      return {
        ...state,
        editedPrograms: state.editedPrograms.filter((_, i) => i !== action.payload.programIndex),
      };
    case 'ADD_PROGRAM': {
      const newProgram: ExtractedProgram = {
        program_name: 'New Program',
        program_code: 'NEW',
        credit_tier: 'A',
        min_fit_score: 60,
        description: '',
        eligibility_conditions: {},
        rate_metadata: { base_rates: [], adjustments: [] },
        rules: [],
      };
      return {
        ...state,
        editedPrograms: [...state.editedPrograms, newProgram],
      };
    }
    case 'TOGGLE_PROGRAM': {
      const newExpanded = new Set(state.expandedPrograms);
      if (newExpanded.has(action.payload.programIndex)) {
        newExpanded.delete(action.payload.programIndex);
      } else {
        newExpanded.add(action.payload.programIndex);
      }
      return {
        ...state,
        expandedPrograms: newExpanded,
      };
    }
    default:
      return state;
  }
}

export function PolicyEditor({ lender, programs, onUpdate }: PolicyEditorProps) {
  const [state, dispatch] = useReducer(editorReducer, {
    editedLender: lender,
    editedPrograms: programs,
    expandedPrograms: new Set([0]),
  });

  // Reset state when props change (e.g., new extraction loaded)
  useEffect(() => {
    dispatch({ type: 'INIT', payload: { lender, programs } });
  }, [lender, programs]);

  // Handler functions
  const toggleProgram = (index: number) => {
    dispatch({ type: 'TOGGLE_PROGRAM', payload: { programIndex: index } });
  };

  const updateLenderField = (field: keyof ExtractedLender, value: unknown) => {
    dispatch({ type: 'UPDATE_LENDER_FIELD', payload: { field, value } });
  };

  const updateProgramField = (programIndex: number, field: keyof ExtractedProgram, value: unknown) => {
    dispatch({ type: 'UPDATE_PROGRAM_FIELD', payload: { programIndex, field, value } });
  };

  const updateRule = (programIndex: number, ruleIndex: number, rule: ExtractedRule) => {
    dispatch({ type: 'UPDATE_RULE', payload: { programIndex, ruleIndex, rule } });
  };

  const deleteRule = (programIndex: number, ruleIndex: number) => {
    dispatch({ type: 'DELETE_RULE', payload: { programIndex, ruleIndex } });
  };

  const addRule = (programIndex: number) => {
    dispatch({ type: 'ADD_RULE', payload: { programIndex } });
  };

  const deleteProgram = (programIndex: number) => {
    dispatch({ type: 'DELETE_PROGRAM', payload: { programIndex } });
  };

  const addProgram = () => {
    dispatch({ type: 'ADD_PROGRAM' });
  };

  const saveChanges = () => {
    onUpdate(state.editedLender, state.editedPrograms);
  };

  return (
    <div className="space-y-6">
      {/* Lender Information */}
      <Card>
        <CardHeader>
          <CardTitle>Lender Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="lender-name">
              Lender Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="lender-name"
              value={state.editedLender.name}
              onChange={(e) => updateLenderField('name', e.target.value)}
              className={!state.editedLender.name ? 'border-red-500' : ''}
            />
            {!state.editedLender.name && (
              <p className="text-xs text-red-500">Required field - please enter lender name</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="lender-description">Description</Label>
            <Textarea
              id="lender-description"
              value={state.editedLender.description || ''}
              onChange={(e) => updateLenderField('description', e.target.value)}
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min-loan">
                Min Loan Amount <span className="text-red-500">*</span>
              </Label>
              <Input
                id="min-loan"
                type="number"
                value={state.editedLender.min_loan_amount}
                onChange={(e) => updateLenderField('min_loan_amount', parseFloat(e.target.value))}
                className={!state.editedLender.min_loan_amount || state.editedLender.min_loan_amount === 0 ? 'border-red-500' : ''}
              />
              {(!state.editedLender.min_loan_amount || state.editedLender.min_loan_amount === 0) && (
                <p className="text-xs text-red-500">Required - typical minimum is $10,000</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="max-loan">
                Max Loan Amount <span className="text-red-500">*</span>
              </Label>
              <Input
                id="max-loan"
                type="number"
                value={state.editedLender.max_loan_amount}
                onChange={(e) => updateLenderField('max_loan_amount', parseFloat(e.target.value))}
                className={!state.editedLender.max_loan_amount || state.editedLender.max_loan_amount === 0 ? 'border-red-500' : ''}
              />
              {(!state.editedLender.max_loan_amount || state.editedLender.max_loan_amount === 0) && (
                <p className="text-xs text-red-500">Required - typical maximum is $5,000,000</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="excluded-states">Excluded States (comma-separated)</Label>
            <Input
              id="excluded-states"
              value={state.editedLender.excluded_states?.join(', ') || ''}
              onChange={(e) =>
                updateLenderField(
                  'excluded_states',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                )
              }
              placeholder="CA, NV, ND, VT"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="excluded-industries">Excluded Industries (comma-separated)</Label>
            <Input
              id="excluded-industries"
              value={state.editedLender.excluded_industries?.join(', ') || ''}
              onChange={(e) =>
                updateLenderField(
                  'excluded_industries',
                  e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                )
              }
              placeholder="Cannabis, Gambling"
            />
          </div>
        </CardContent>
      </Card>

      {/* Programs */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Programs ({state.editedPrograms.length})</h3>
          <Button onClick={addProgram} size="sm">
            <Plus className="w-4 h-4 mr-2" />
            Add Program
          </Button>
        </div>

        {state.editedPrograms.map((program, programIndex) => (
          <Card key={programIndex} className="overflow-hidden">
            <div
              className={`p-4 flex items-center justify-between cursor-pointer hover:bg-muted/50 transition-colors ${state.expandedPrograms.has(programIndex) ? 'border-b' : ''
                }`}
              onClick={() => toggleProgram(programIndex)}
            >
              <div className="flex items-center space-x-3">
                {state.expandedPrograms.has(programIndex) ? (
                  <ChevronUp className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{program.program_name}</span>
                    <Badge variant="outline" className="text-xs">
                      {program.program_code}
                    </Badge>
                  </div>
                  <div className="flex gap-2 text-sm text-muted-foreground mt-1">
                    <span>Tier: {program.credit_tier}</span>
                    <span>•</span>
                    <span>{program.rules?.length || 0} rules</span>
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteProgram(programIndex);
                }}
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="w-5 h-5" />
              </Button>
            </div>

            {state.expandedPrograms.has(programIndex) && (
              <CardContent className="p-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`prog-name-${programIndex}`}>
                      Program Name <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id={`prog-name-${programIndex}`}
                      value={program.program_name}
                      onChange={(e) =>
                        updateProgramField(programIndex, 'program_name', e.target.value)
                      }
                      className={!program.program_name ? 'border-red-500' : ''}
                    />
                    {!program.program_name && (
                      <p className="text-xs text-red-500">Required field</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`prog-code-${programIndex}`}>
                      Program Code <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id={`prog-code-${programIndex}`}
                      value={program.program_code}
                      onChange={(e) =>
                        updateProgramField(programIndex, 'program_code', e.target.value)
                      }
                      className={!program.program_code ? 'border-red-500' : ''}
                    />
                    {!program.program_code && (
                      <p className="text-xs text-red-500">Required field (e.g., "A", "Tier 1")</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`prog-tier-${programIndex}`}>
                      Credit Tier <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id={`prog-tier-${programIndex}`}
                      value={program.credit_tier}
                      onChange={(e) =>
                        updateProgramField(programIndex, 'credit_tier', e.target.value)
                      }
                      className={!program.credit_tier ? 'border-red-500' : ''}
                      placeholder="e.g., A, B, C"
                    />
                    {!program.credit_tier && (
                      <p className="text-xs text-red-500">Required (e.g., "A", "B", "C")</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor={`prog-score-${programIndex}`}>Min Fit Score</Label>
                    <Input
                      id={`prog-score-${programIndex}`}
                      type="number"
                      value={program.min_fit_score || 60}
                      onChange={(e) =>
                        updateProgramField(programIndex, 'min_fit_score', parseFloat(e.target.value))
                      }
                      placeholder="Default: 60"
                    />
                    <p className="text-xs text-muted-foreground">0-100, default is 60</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`prog-desc-${programIndex}`}>Description</Label>
                  <Textarea
                    id={`prog-desc-${programIndex}`}
                    value={program.description || ''}
                    onChange={(e) =>
                      updateProgramField(programIndex, 'description', e.target.value)
                    }
                    rows={2}
                    placeholder="Brief description of this program"
                  />
                </div>

                {/* Rate Metadata Warning */}
                {(!program.rate_metadata?.base_rates || program.rate_metadata.base_rates.length === 0) && (
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                    <p className="text-sm text-yellow-800 font-medium">
                      ⚠️ Rate Information Missing
                    </p>
                    <p className="text-xs text-yellow-700 mt-1">
                      This program has no rate tables defined. Add rate information in the JSON editor below or the rules section.
                    </p>
                  </div>
                )}

                {/* Rules */}
                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between mb-4">
                    <h5 className="font-medium">Rules ({program.rules?.length || 0})</h5>
                    <Button
                      onClick={() => addRule(programIndex)}
                      size="sm"
                      variant="secondary"
                      className="h-8"
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Add Rule
                    </Button>
                  </div>

                  {(!program.rules || program.rules.length === 0) && (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md mb-3">
                      <p className="text-sm text-yellow-800 font-medium">
                        ⚠️ No Rules Defined
                      </p>
                      <p className="text-xs text-yellow-700 mt-1">
                        This program has no underwriting rules. Click "Add Rule" to define credit, loan amount, or equipment requirements.
                      </p>
                    </div>
                  )}

                  <div className="space-y-3">
                    {program.rules?.map((rule, ruleIndex) => (
                      <div
                        key={ruleIndex}
                        className="p-4 bg-muted/30 rounded-lg border flex gap-4"
                      >
                        <div className="flex-1 space-y-3">
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <Input
                                value={rule.rule_name}
                                onChange={(e) =>
                                  updateRule(programIndex, ruleIndex, {
                                    ...rule,
                                    rule_name: e.target.value,
                                  })
                                }
                                placeholder="Rule Name *"
                                className={`h-8 text-sm ${!rule.rule_name ? 'border-red-500' : ''}`}
                              />
                              {!rule.rule_name && (
                                <p className="text-xs text-red-500 mt-1">Required</p>
                              )}
                            </div>
                            <div>
                              <Input
                                value={rule.rule_type}
                                onChange={(e) =>
                                  updateRule(programIndex, ruleIndex, {
                                    ...rule,
                                    rule_type: e.target.value,
                                  })
                                }
                                placeholder="Rule Type * (e.g., min_fico)"
                                className={`h-8 text-sm ${!rule.rule_type ? 'border-red-500' : ''}`}
                              />
                              {!rule.rule_type && (
                                <p className="text-xs text-red-500 mt-1">Required</p>
                              )}
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <Input
                              type="number"
                              step="0.1"
                              value={rule.weight || 1.0}
                              onChange={(e) =>
                                updateRule(programIndex, ruleIndex, {
                                  ...rule,
                                  weight: parseFloat(e.target.value),
                                })
                              }
                              placeholder="Weight"
                              className="h-8 text-sm"
                            />
                            <div className="flex items-center space-x-2 h-8">
                              <Checkbox
                                id={`rule-mandatory-${programIndex}-${ruleIndex}`}
                                checked={rule.is_mandatory !== false}
                                onCheckedChange={(checked) =>
                                  updateRule(programIndex, ruleIndex, {
                                    ...rule,
                                    is_mandatory: checked as boolean
                                  })
                                }
                              />
                              <Label htmlFor={`rule-mandatory-${programIndex}-${ruleIndex}`} className="text-sm cursor-pointer">
                                Mandatory
                              </Label>
                            </div>
                          </div>
                          <div>
                            <Textarea
                              value={JSON.stringify(rule.criteria, null, 2)}
                              onChange={(e) => {
                                try {
                                  const criteria = JSON.parse(e.target.value);
                                  updateRule(programIndex, ruleIndex, { ...rule, criteria });
                                } catch { }
                              }}
                              placeholder='Criteria (JSON) * - e.g., {"min_score": 650}'
                              rows={2}
                              className={`font-mono text-xs min-h-[60px] ${!rule.criteria || Object.keys(rule.criteria).length === 0 ? 'border-red-500' : ''}`}
                            />
                            {(!rule.criteria || Object.keys(rule.criteria).length === 0) && (
                              <p className="text-xs text-red-500 mt-1">Required - must be valid JSON</p>
                            )}
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteRule(programIndex, ruleIndex)}
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            )}
          </Card>
        ))}
      </div>

      {/* Save Changes Button */}
      <div className="flex justify-end">
        <Button onClick={saveChanges} size="lg" className="min-w-[200px]">
          Save Changes
        </Button>
      </div>
    </div>
  );
}
