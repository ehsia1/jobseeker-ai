'use client';

import { useState } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import JDAnalyzer from '@/components/features/JDAnalyzer';
import ProposalGenerator from '@/components/features/ProposalGenerator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
// Button available if needed
import {
  FileSearch,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { useJDParserHealth, useProposalsHealth } from '@/hooks/useAPI';
import type { ParsedJD, ScoreBreakdown, GeneratedProposal } from '@/lib/types';

export default function AnalyzePage() {
  const [parsedJD, setParsedJD] = useState<ParsedJD | null>(null);
  const [, setMatchScore] = useState<ScoreBreakdown | null>(null);
  const [generatedProposal, setGeneratedProposal] = useState<GeneratedProposal | null>(null);

  const { status: jdParserStatus, llmAvailable: jdLlmAvailable, loading: jdHealthLoading } = useJDParserHealth();
  const { status: proposalsStatus, llmAvailable: proposalsLlmAvailable, demoMode, loading: proposalsHealthLoading } = useProposalsHealth();

  const handleJDParsed = (parsed: ParsedJD, score?: ScoreBreakdown) => {
    setParsedJD(parsed);
    setMatchScore(score || null);
    setGeneratedProposal(null);
  };

  const handleProposalGenerated = (proposal: GeneratedProposal) => {
    setGeneratedProposal(proposal);
  };

  const isHealthy = jdParserStatus === 'healthy' && proposalsStatus === 'healthy';
  const isLoading = jdHealthLoading || proposalsHealthLoading;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
              <FileSearch className="w-8 h-8 text-blue-500" />
              Analyze & Generate
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-2">
              Analyze job descriptions and generate tailored proposals instantly
            </p>
          </div>

          {/* Service Status */}
          <div className="flex items-center gap-3">
            {isLoading ? (
              <Badge variant="outline" className="flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                Checking services...
              </Badge>
            ) : isHealthy ? (
              <>
                <Badge variant="outline" className="flex items-center gap-1 text-green-600 border-green-200">
                  <CheckCircle className="w-3 h-3" />
                  AI Ready
                </Badge>
                {demoMode && (
                  <Badge variant="secondary" className="text-xs">
                    Demo Mode
                  </Badge>
                )}
              </>
            ) : (
              <Badge variant="destructive" className="flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Service Unavailable
              </Badge>
            )}
          </div>
        </div>

        {/* Service Warning */}
        {!isLoading && !isHealthy && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Some AI services are currently unavailable. Please ensure the backend is running with Ollama or OpenAI configured.
              {!jdLlmAvailable && ' JD Parser LLM is not available.'}
              {!proposalsLlmAvailable && ' Proposals LLM is not available.'}
            </AlertDescription>
          </Alert>
        )}

        {/* Demo Mode Info */}
        {demoMode && (
          <Alert className="bg-blue-50 border-blue-200">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-blue-800">
              <strong>Demo Mode Active:</strong> Running with local Ollama. No API keys or usage limits apply.
              For production, configure OpenAI or Anthropic API keys.
            </AlertDescription>
          </Alert>
        )}

        {/* Workflow Steps */}
        <div className="flex items-center justify-center gap-4 py-2">
          <div className={`flex items-center gap-2 ${parsedJD ? 'text-green-600' : 'text-muted-foreground'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              parsedJD ? 'bg-green-100 text-green-600' : 'bg-muted'
            }`}>
              1
            </div>
            <span className="text-sm font-medium hidden sm:inline">Analyze JD</span>
          </div>
          <div className={`h-px w-12 ${parsedJD ? 'bg-green-300' : 'bg-muted'}`} />
          <div className={`flex items-center gap-2 ${generatedProposal ? 'text-green-600' : parsedJD ? 'text-blue-600' : 'text-muted-foreground'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              generatedProposal ? 'bg-green-100 text-green-600' : parsedJD ? 'bg-blue-100 text-blue-600' : 'bg-muted'
            }`}>
              2
            </div>
            <span className="text-sm font-medium hidden sm:inline">Generate Proposal</span>
          </div>
          <div className={`h-px w-12 ${generatedProposal ? 'bg-green-300' : 'bg-muted'}`} />
          <div className={`flex items-center gap-2 ${generatedProposal ? 'text-green-600' : 'text-muted-foreground'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              generatedProposal ? 'bg-green-100 text-green-600' : 'bg-muted'
            }`}>
              3
            </div>
            <span className="text-sm font-medium hidden sm:inline">Enhance & Copy</span>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Left Column: JD Analyzer */}
          <JDAnalyzer onParsed={handleJDParsed} />

          {/* Right Column: Proposal Generator */}
          <ProposalGenerator
            parsedJD={parsedJD}
            onProposalGenerated={handleProposalGenerated}
          />
        </div>

        {/* Tips Section */}
        <div className="bg-muted/50 rounded-lg p-4">
          <h3 className="font-medium mb-2 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-500" />
            Tips for Better Proposals
          </h3>
          <ul className="grid md:grid-cols-2 gap-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-purple-500">•</span>
              Paste the complete job description for accurate skill extraction
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-500">•</span>
              Use the &quot;Additional Context&quot; field to highlight specific experiences
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-500">•</span>
              Try different tones - Short for quick applies, Full for dream jobs
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-500">•</span>
              Use enhancement options to add keywords or metrics after generation
            </li>
          </ul>
        </div>
      </div>
    </AppLayout>
  );
}
