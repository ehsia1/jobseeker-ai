'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Copy,
  Check,
  Loader2,
  RefreshCw,
  FileText,
  Sparkles,
  Building2,
} from 'lucide-react';
import { Job, ScoredJob, AllTonesResponse } from '@/lib/types';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

interface ProposalModalProps {
  job: Job | ScoredJob;
  open: boolean;
  onClose: () => void;
}

interface ProposalData {
  short: string;
  full: string;
  keywords_used: string[];
}

export default function ProposalModal({
  job,
  open,
  onClose,
}: ProposalModalProps) {
  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState<ProposalData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedShort, setCopiedShort] = useState(false);
  const [copiedFull, setCopiedFull] = useState(false);
  const [activeTab, setActiveTab] = useState('short');

  useEffect(() => {
    if (open && !proposal && !loading) {
      generateProposals();
    }
  }, [open]);

  useEffect(() => {
    if (!open) {
      // Reset state when modal closes
      setProposal(null);
      setError(null);
      setCopiedShort(false);
      setCopiedFull(false);
      setActiveTab('short');
    }
  }, [open]);

  const generateProposals = async () => {
    setLoading(true);
    setError(null);

    try {
      const response: AllTonesResponse = await apiClient.generateAllTones({
        job_id: job.id,
      });
      setProposal({
        short: response.short?.content || '',
        full: response.full?.content || '',
        keywords_used: response.short?.keywords_used || response.full?.keywords_used || [],
      });
    } catch (err) {
      const errorMessage =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ||
        (err as Error)?.message ||
        'Failed to generate proposal';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string, type: 'short' | 'full') => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'short') {
        setCopiedShort(true);
        setTimeout(() => setCopiedShort(false), 2000);
      } else {
        setCopiedFull(true);
        setTimeout(() => setCopiedFull(false), 2000);
      }
      toast.success('Copied to clipboard!');
    } catch (err) {
      toast.error('Failed to copy to clipboard');
    }
  };

  const handleRegenerate = () => {
    setProposal(null);
    generateProposals();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            AI-Generated Proposal
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            {job.title} at {job.company}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-10 h-10 animate-spin text-primary mb-4" />
            <p className="text-lg font-medium">Generating your proposal...</p>
            <p className="text-sm text-gray-600 mt-2">
              Analyzing job requirements and crafting a tailored response
            </p>
          </div>
        ) : error ? (
          <div className="py-8 text-center">
            <p className="text-red-500 mb-4">{error}</p>
            <Button onClick={handleRegenerate}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </div>
        ) : proposal ? (
          <div className="space-y-4">
            {/* Keywords */}
            {proposal.keywords_used && proposal.keywords_used.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-sm text-gray-500">Keywords used:</span>
                {proposal.keywords_used.map((keyword, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {keyword}
                  </Badge>
                ))}
              </div>
            )}

            {/* Proposal Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="short">
                  <FileText className="w-4 h-4 mr-2" />
                  Short Version
                </TabsTrigger>
                <TabsTrigger value="full">
                  <FileText className="w-4 h-4 mr-2" />
                  Full Version
                </TabsTrigger>
              </TabsList>

              <TabsContent value="short" className="mt-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="relative">
                      <Textarea
                        value={proposal.short}
                        readOnly
                        className="min-h-[150px] resize-none bg-gray-50 dark:bg-gray-900"
                      />
                      <Button
                        size="sm"
                        variant="secondary"
                        className="absolute top-2 right-2"
                        onClick={() => copyToClipboard(proposal.short, 'short')}
                      >
                        {copiedShort ? (
                          <>
                            <Check className="w-4 h-4 mr-1" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4 mr-1" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      ~{proposal.short.split(' ').length} words - Perfect for quick applications
                    </p>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="full" className="mt-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="relative">
                      <Textarea
                        value={proposal.full}
                        readOnly
                        className="min-h-[250px] resize-none bg-gray-50 dark:bg-gray-900"
                      />
                      <Button
                        size="sm"
                        variant="secondary"
                        className="absolute top-2 right-2"
                        onClick={() => copyToClipboard(proposal.full, 'full')}
                      >
                        {copiedFull ? (
                          <>
                            <Check className="w-4 h-4 mr-1" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4 mr-1" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      ~{proposal.full.split(' ').length} words - Detailed proposal with experience highlights
                    </p>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={handleRegenerate}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Regenerate
              </Button>
              <Button
                className="flex-1"
                onClick={() =>
                  copyToClipboard(
                    activeTab === 'short' ? proposal.short : proposal.full,
                    activeTab as 'short' | 'full'
                  )
                }
              >
                <Copy className="w-4 h-4 mr-2" />
                Copy {activeTab === 'short' ? 'Short' : 'Full'} Version
              </Button>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
