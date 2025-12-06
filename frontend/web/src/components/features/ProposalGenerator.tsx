'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Sparkles,
  Copy,
  Check,
  Loader2,
  Wand2,
  FileText,
  Zap,
  BookOpen,
  Info,
  RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api/client';
import type { ParsedJD, GeneratedProposal, AllTonesResponse, ProposalTone, EnhancementType } from '@/lib/types';

interface ProposalGeneratorProps {
  parsedJD: ParsedJD | null;
  jobId?: string;
  onProposalGenerated?: (proposal: GeneratedProposal) => void;
}

const TONE_INFO = {
  short: {
    icon: Zap,
    label: 'Short',
    description: '50-75 words. Direct and punchy.',
    color: 'text-yellow-600',
  },
  medium: {
    icon: FileText,
    label: 'Medium',
    description: '150-200 words. Professional and balanced.',
    color: 'text-blue-600',
  },
  full: {
    icon: BookOpen,
    label: 'Full',
    description: '300-400 words. Comprehensive with examples.',
    color: 'text-purple-600',
  },
};

const ENHANCEMENT_OPTIONS: { value: EnhancementType; label: string; description: string }[] = [
  { value: 'add_keywords', label: 'Add Keywords', description: 'Incorporate relevant terms from the JD' },
  { value: 'improve_tone', label: 'Improve Tone', description: 'Make more professional and engaging' },
  { value: 'add_metrics', label: 'Add Metrics', description: 'Include quantified achievements' },
  { value: 'shorten', label: 'Shorten', description: 'Make more concise' },
  { value: 'expand', label: 'Expand', description: 'Add more detail and examples' },
];

export default function ProposalGenerator({
  parsedJD,
  jobId,
  onProposalGenerated,
}: ProposalGeneratorProps) {
  const [selectedTone, setSelectedTone] = useState<ProposalTone>('medium');
  const [additionalContext, setAdditionalContext] = useState('');
  const [proposals, setProposals] = useState<AllTonesResponse | null>(null);
  const [currentProposal, setCurrentProposal] = useState<GeneratedProposal | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [enhancing, setEnhancing] = useState(false);
  const [selectedEnhancements, setSelectedEnhancements] = useState<EnhancementType[]>([
    'improve_tone',
    'add_keywords',
  ]);
  const [editableProposal, setEditableProposal] = useState('');

  // Update editable proposal when current proposal changes
  useEffect(() => {
    if (currentProposal) {
      setEditableProposal(currentProposal.content);
    }
  }, [currentProposal]);

  const generateAllTones = async () => {
    if (!parsedJD && !jobId) {
      toast.error('Please analyze a job description first');
      return;
    }

    setLoading(true);
    try {
      const result = await apiClient.generateAllTones({
        job_id: jobId,
        parsed_jd: parsedJD || undefined,
        additional_context: additionalContext || undefined,
      });

      setProposals(result);
      setCurrentProposal(result[selectedTone]);
      toast.success('Proposals generated successfully!');
      onProposalGenerated?.(result[selectedTone]);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to generate proposals');
    } finally {
      setLoading(false);
    }
  };

  const generateSingleTone = async (tone: ProposalTone) => {
    if (!parsedJD && !jobId) {
      toast.error('Please analyze a job description first');
      return;
    }

    setLoading(true);
    try {
      const result = await apiClient.generateProposal({
        job_id: jobId,
        parsed_jd: parsedJD || undefined,
        tone,
        additional_context: additionalContext || undefined,
      });

      setCurrentProposal(result);
      setProposals((prev) =>
        prev ? { ...prev, [tone]: result } : null
      );
      toast.success(`${TONE_INFO[tone].label} proposal generated!`);
      onProposalGenerated?.(result);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to generate proposal');
    } finally {
      setLoading(false);
    }
  };

  const enhanceProposal = async () => {
    if (!editableProposal.trim()) {
      toast.error('No proposal to enhance');
      return;
    }

    if (selectedEnhancements.length === 0) {
      toast.error('Select at least one enhancement');
      return;
    }

    setEnhancing(true);
    try {
      const result = await apiClient.enhanceProposal({
        original_proposal: editableProposal,
        job_id: jobId,
        parsed_jd: parsedJD || undefined,
        enhancements: selectedEnhancements,
      });

      setEditableProposal(result.enhanced_proposal);
      setCurrentProposal({
        content: result.enhanced_proposal,
        tone: result.tone as ProposalTone,
        word_count: result.word_count,
        keywords_used: result.keywords_used,
        experience_highlighted: [],
      });
      toast.success('Proposal enhanced!');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to enhance proposal');
    } finally {
      setEnhancing(false);
    }
  };

  const copyToClipboard = async () => {
    const textToCopy = editableProposal || currentProposal?.content;
    if (!textToCopy) return;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      toast.success('Copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy');
    }
  };

  const handleToneChange = (tone: ProposalTone) => {
    setSelectedTone(tone);
    if (proposals && proposals[tone]) {
      setCurrentProposal(proposals[tone]);
    }
  };

  const toggleEnhancement = (enhancement: EnhancementType) => {
    setSelectedEnhancements((prev) =>
      prev.includes(enhancement)
        ? prev.filter((e) => e !== enhancement)
        : [...prev, enhancement]
    );
  };

  const isReady = parsedJD || jobId;

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-500" />
          Proposal Generator
        </CardTitle>
        <CardDescription>
          Generate tailored proposals in multiple tones
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4">
        {/* Tone Selection */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            Select Tone
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">
                    Choose between short, medium, or full-length proposals
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </Label>

          <div className="grid grid-cols-3 gap-2">
            {(Object.keys(TONE_INFO) as ProposalTone[]).map((tone) => {
              const info = TONE_INFO[tone];
              const Icon = info.icon;
              const isSelected = selectedTone === tone;

              return (
                <TooltipProvider key={tone}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant={isSelected ? 'default' : 'outline'}
                        className="flex flex-col h-auto py-3 gap-1"
                        onClick={() => handleToneChange(tone)}
                      >
                        <Icon className={`w-4 h-4 ${isSelected ? '' : info.color}`} />
                        <span className="text-xs font-medium">{info.label}</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{info.description}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              );
            })}
          </div>
        </div>

        {/* Additional Context */}
        <div className="space-y-2">
          <Label htmlFor="context">Additional Context (Optional)</Label>
          <Textarea
            id="context"
            placeholder="Add any specific points to mention (e.g., relevant project, specific experience)..."
            value={additionalContext}
            onChange={(e) => setAdditionalContext(e.target.value)}
            className="h-20 resize-none"
          />
        </div>

        {/* Generate Buttons */}
        <div className="flex gap-2">
          <Button
            className="flex-1"
            onClick={generateAllTones}
            disabled={loading || !isReady}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Generate All Tones
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={() => generateSingleTone(selectedTone)}
            disabled={loading || !isReady}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Regenerate
          </Button>
        </div>

        {/* Generated Proposal */}
        {currentProposal && (
          <div className="flex-1 flex flex-col space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label>Generated Proposal</Label>
                <Badge variant="outline">{currentProposal.word_count} words</Badge>
              </div>
              <Button variant="ghost" size="sm" onClick={copyToClipboard}>
                {copied ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
            </div>

            <Tabs defaultValue="preview" className="flex-1 flex flex-col">
              <TabsList className="grid grid-cols-2 w-full">
                <TabsTrigger value="preview">Preview</TabsTrigger>
                <TabsTrigger value="edit">Edit & Enhance</TabsTrigger>
              </TabsList>

              <TabsContent value="preview" className="flex-1">
                <div className="bg-muted/50 rounded-lg p-4 h-48 overflow-y-auto">
                  <p className="whitespace-pre-wrap text-sm">
                    {currentProposal.content}
                  </p>
                </div>

                {/* Keywords Used */}
                {currentProposal.keywords_used.length > 0 && (
                  <div className="mt-3 space-y-1">
                    <Label className="text-xs text-muted-foreground">
                      Keywords Used:
                    </Label>
                    <div className="flex flex-wrap gap-1">
                      {currentProposal.keywords_used.map((keyword) => (
                        <Badge key={keyword} variant="secondary" className="text-xs">
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="edit" className="flex-1 space-y-3">
                <Textarea
                  value={editableProposal}
                  onChange={(e) => setEditableProposal(e.target.value)}
                  className="h-40 resize-none"
                  placeholder="Edit your proposal here..."
                />

                {/* Enhancement Options */}
                <div className="space-y-2">
                  <Label className="text-xs">Enhancement Options:</Label>
                  <div className="flex flex-wrap gap-1.5">
                    {ENHANCEMENT_OPTIONS.map((option) => (
                      <TooltipProvider key={option.value}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge
                              variant={
                                selectedEnhancements.includes(option.value)
                                  ? 'default'
                                  : 'outline'
                              }
                              className="cursor-pointer"
                              onClick={() => toggleEnhancement(option.value)}
                            >
                              {option.label}
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>{option.description}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ))}
                  </div>
                </div>

                <Button
                  className="w-full"
                  variant="secondary"
                  onClick={enhanceProposal}
                  disabled={enhancing || !editableProposal.trim()}
                >
                  {enhancing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Enhancing...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4 mr-2" />
                      Enhance Proposal
                    </>
                  )}
                </Button>
              </TabsContent>
            </Tabs>
          </div>
        )}

        {/* Empty State */}
        {!currentProposal && !loading && (
          <div className="flex-1 flex items-center justify-center border-2 border-dashed rounded-lg">
            <div className="text-center text-muted-foreground p-8">
              <Sparkles className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p className="text-sm">
                {isReady
                  ? 'Click "Generate All Tones" to create proposals'
                  : 'Analyze a job description to generate proposals'}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
