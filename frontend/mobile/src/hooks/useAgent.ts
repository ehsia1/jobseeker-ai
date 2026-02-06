/**
 * Agent Hooks
 * React Query hooks for AI agent run/poll/result pattern
 */

import { useState, useCallback, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { agentApi } from '../api/client';
import type {
  AgentStatus,
  AgentRunResponse,
  AgentStatusResponse,
  JobRadarRequest,
  JobRadarResult,
  CoverLetterRequest,
  CoverLetterResult,
  ResumeOptimizeRequest,
  ResumeOptimizeResult,
  InterviewPrepRequest,
  InterviewPrepResult,
  SalaryResearchRequest,
  SalaryResearchResult,
  SkillGapRequest,
  SkillGapResult,
  ApplicationTrackerRequest,
  ApplicationTrackerResult,
  NetworkIntelligenceRequest,
  NetworkIntelligenceResult,
  AutoApplyRequest,
  AutoApplyResult,
} from '@jobseeker/shared';

// Polling interval in ms
const POLL_INTERVAL = 1000;

// Generic agent state
interface AgentState<TResult> {
  runId: string | null;
  status: AgentStatus | null;
  progress: number;
  currentStep: string;
  messages: string[];
  errors: string[];
  result: TResult | null;
}

// Generic agent hook return type
interface UseAgentReturn<TRequest, TResult> {
  run: (request: TRequest) => void;
  reset: () => void;
  isIdle: boolean;
  isRunning: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  runId: string | null;
  status: AgentStatus | null;
  progress: number;
  currentStep: string;
  messages: string[];
  errors: string[];
  result: TResult | null;
  error: Error | null;
}

// ============= Job Radar Hook =============
export function useJobRadar(): UseAgentReturn<JobRadarRequest, JobRadarResult> {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AgentState<JobRadarResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  // Start the agent run
  const runMutation = useMutation({
    mutationFn: (request: JobRadarRequest) => agentApi.runJobRadar(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  // Poll status while running
  const statusQuery = useQuery({
    queryKey: ['agent', 'radar', 'status', state.runId],
    queryFn: () => agentApi.getJobRadarStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  // Update state from status polling
  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  // Fetch result when completed
  const resultQuery = useQuery({
    queryKey: ['agent', 'radar', 'result', state.runId],
    queryFn: () => agentApi.getJobRadarResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  // Update state with result
  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
      // Invalidate jobs/matches queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    }
  }, [resultQuery.data, queryClient]);

  const run = useCallback((request: JobRadarRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Cover Letter Hook =============
export function useCoverLetter(): UseAgentReturn<CoverLetterRequest, CoverLetterResult> {
  const [state, setState] = useState<AgentState<CoverLetterResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: CoverLetterRequest) => agentApi.runCoverLetter(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'cover-letter', 'status', state.runId],
    queryFn: () => agentApi.getCoverLetterStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'cover-letter', 'result', state.runId],
    queryFn: () => agentApi.getCoverLetterResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: CoverLetterRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Resume Optimizer Hook =============
export function useResumeOptimizer(): UseAgentReturn<ResumeOptimizeRequest, ResumeOptimizeResult> {
  const [state, setState] = useState<AgentState<ResumeOptimizeResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: ResumeOptimizeRequest) => agentApi.runResumeOptimize(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'resume', 'status', state.runId],
    queryFn: () => agentApi.getResumeOptimizeStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'resume', 'result', state.runId],
    queryFn: () => agentApi.getResumeOptimizeResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: ResumeOptimizeRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Interview Prep Hook =============
export function useInterviewPrep(): UseAgentReturn<InterviewPrepRequest, InterviewPrepResult> {
  const [state, setState] = useState<AgentState<InterviewPrepResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: InterviewPrepRequest) => agentApi.runInterviewPrep(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'interview', 'status', state.runId],
    queryFn: () => agentApi.getInterviewPrepStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'interview', 'result', state.runId],
    queryFn: () => agentApi.getInterviewPrepResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: InterviewPrepRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Salary Research Hook =============
export function useSalaryResearch(): UseAgentReturn<SalaryResearchRequest, SalaryResearchResult> {
  const [state, setState] = useState<AgentState<SalaryResearchResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: SalaryResearchRequest) => agentApi.runSalaryResearch(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'salary', 'status', state.runId],
    queryFn: () => agentApi.getSalaryResearchStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'salary', 'result', state.runId],
    queryFn: () => agentApi.getSalaryResearchResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: SalaryResearchRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Skill Gap Hook =============
export function useSkillGap(): UseAgentReturn<SkillGapRequest, SkillGapResult> {
  const [state, setState] = useState<AgentState<SkillGapResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: SkillGapRequest) => agentApi.runSkillGap(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'skill-gap', 'status', state.runId],
    queryFn: () => agentApi.getSkillGapStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'skill-gap', 'result', state.runId],
    queryFn: () => agentApi.getSkillGapResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: SkillGapRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Application Tracker Hook =============
export function useApplicationTracker(): UseAgentReturn<ApplicationTrackerRequest, ApplicationTrackerResult> {
  const [state, setState] = useState<AgentState<ApplicationTrackerResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: ApplicationTrackerRequest) => agentApi.runApplicationTracker(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'tracker', 'status', state.runId],
    queryFn: () => agentApi.getApplicationTrackerStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'tracker', 'result', state.runId],
    queryFn: () => agentApi.getApplicationTrackerResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: ApplicationTrackerRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Network Intelligence Hook =============
export function useNetworkIntelligence(): UseAgentReturn<NetworkIntelligenceRequest, NetworkIntelligenceResult> {
  const [state, setState] = useState<AgentState<NetworkIntelligenceResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: NetworkIntelligenceRequest) => agentApi.runNetworkIntelligence(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'network', 'status', state.runId],
    queryFn: () => agentApi.getNetworkIntelligenceStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'network', 'result', state.runId],
    queryFn: () => agentApi.getNetworkIntelligenceResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: NetworkIntelligenceRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}

// ============= Auto-Apply Hook =============
export function useAutoApply(): UseAgentReturn<AutoApplyRequest, AutoApplyResult> {
  const [state, setState] = useState<AgentState<AutoApplyResult>>({
    runId: null,
    status: null,
    progress: 0,
    currentStep: '',
    messages: [],
    errors: [],
    result: null,
  });
  const [error, setError] = useState<Error | null>(null);

  const runMutation = useMutation({
    mutationFn: (request: AutoApplyRequest) => agentApi.runAutoApply(request),
    onSuccess: (data: AgentRunResponse) => {
      setState(prev => ({
        ...prev,
        runId: data.run_id,
        status: data.status,
        messages: data.message ? [data.message] : [],
      }));
      setError(null);
    },
    onError: (err: Error) => {
      setError(err);
    },
  });

  const statusQuery = useQuery({
    queryKey: ['agent', 'apply', 'status', state.runId],
    queryFn: () => agentApi.getAutoApplyStatus(state.runId!),
    enabled: !!state.runId && (state.status === 'pending' || state.status === 'running'),
    refetchInterval: POLL_INTERVAL,
  });

  useEffect(() => {
    if (statusQuery.data) {
      const data = statusQuery.data;
      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress_percent,
        currentStep: data.current_step,
        messages: data.messages,
        errors: data.errors,
      }));
    }
  }, [statusQuery.data]);

  const resultQuery = useQuery({
    queryKey: ['agent', 'apply', 'result', state.runId],
    queryFn: () => agentApi.getAutoApplyResult(state.runId!),
    enabled: !!state.runId && state.status === 'completed',
  });

  useEffect(() => {
    if (resultQuery.data) {
      setState(prev => ({
        ...prev,
        result: resultQuery.data,
      }));
    }
  }, [resultQuery.data]);

  const run = useCallback((request: AutoApplyRequest) => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
    runMutation.mutate(request);
  }, [runMutation]);

  const reset = useCallback(() => {
    setState({
      runId: null,
      status: null,
      progress: 0,
      currentStep: '',
      messages: [],
      errors: [],
      result: null,
    });
    setError(null);
  }, []);

  return {
    run,
    reset,
    isIdle: !state.runId && !runMutation.isPending,
    isRunning: state.status === 'pending' || state.status === 'running' || runMutation.isPending,
    isCompleted: state.status === 'completed',
    isFailed: state.status === 'failed',
    runId: state.runId,
    status: state.status,
    progress: state.progress,
    currentStep: state.currentStep,
    messages: state.messages,
    errors: state.errors,
    result: state.result,
    error: error || statusQuery.error as Error || resultQuery.error as Error || null,
  };
}
