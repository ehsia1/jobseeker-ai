# AI Agents Integration Guide

This document maps the 9 AI agents to their corresponding frontend views and defines the integration strategy.

## Philosophy

Agents are **contextually integrated** into existing views rather than living in separate dashboards. This ensures:
- Users discover AI features naturally within their workflow
- Agents receive relevant context automatically (current job, profile data, etc.)
- The experience feels cohesive rather than fragmented

---

## Agent-to-View Mapping

| Agent | Primary View | Trigger | Context Provided |
|-------|-------------|---------|------------------|
| **Cover Letter** | Job Details | "Generate Cover Letter" button | Job ID, user profile |
| **Job Radar** | Jobs Feed | Pull-to-refresh, "Find Jobs" button | User preferences, skills |
| **Resume Optimizer** | Profile / Resume | "Optimize Resume" button | Current resume, target job (optional) |
| **Application Tracker** | Matches / Dashboard | Daily briefing card, app load | All saved/applied jobs |
| **Interview Prep** | Job Details | Status = "interviewing" | Job details, user profile |
| **Salary Research** | Job Details | Salary section, "Research Salary" | Job title, location, skills |
| **Skill Gap** | Profile / Job Details | "Analyze Skills" button | User skills vs job requirements |
| **Network Intelligence** | Profile / Job Details | "Find Connections" button | Target company, user network |
| **Auto-Apply** | Job Details | "Prepare Application" button | Job, resume, cover letter |

---

## Detailed View Integration

### 1. Job Details View (`/job/[id]`)

**Agents:**
- **Cover Letter Generator** - Primary CTA for proposal/cover letter generation
- **Salary Research** - Shows market rate data in salary section
- **Interview Prep** - Appears when match status is "interviewing"
- **Skill Gap Analysis** - Shows skill match percentage with improvement suggestions
- **Auto-Apply** - "Prepare Application" bundles resume + cover letter

**UI Components:**
```
┌─────────────────────────────────────┐
│ Job Title @ Company                 │
│ Location • Remote • $X-Y/hr         │
├─────────────────────────────────────┤
│ [Generate Cover Letter] [Save Job]  │  ← Cover Letter Agent
├─────────────────────────────────────┤
│ Skill Match: 85%                    │  ← Skill Gap Agent
│ ✓ React  ✓ TypeScript  ✗ GraphQL   │
│ [View Skill Gap Analysis]           │
├─────────────────────────────────────┤
│ Salary Insights                     │  ← Salary Research Agent
│ Market Rate: $45-65/hr              │
│ [Get Detailed Research]             │
├─────────────────────────────────────┤
│ Description...                      │
├─────────────────────────────────────┤
│ [Prepare Full Application]          │  ← Auto-Apply Agent
└─────────────────────────────────────┘
```

**When status = "interviewing":**
```
┌─────────────────────────────────────┐
│ 🎯 Interview Prep Available         │  ← Interview Prep Agent
│ Prepare for your upcoming interview │
│ [Start Prep Session]                │
└─────────────────────────────────────┘
```

### 2. Jobs Feed View (`/jobs` or `/feed`)

**Agents:**
- **Job Radar** - Intelligent job discovery based on preferences

**UI Triggers:**
- Pull-to-refresh activates radar scan
- "Find More Jobs" button in empty/end state
- Background refresh with notification badge

**UI Components:**
```
┌─────────────────────────────────────┐
│ Your Job Feed                       │
│ ┌─────────────────────────────────┐ │
│ │ 🔍 Job Radar Active             │ │  ← Job Radar Agent
│ │ Finding jobs matching your      │ │
│ │ profile...                      │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [Job Card 1]                        │
│ [Job Card 2]                        │
│ ...                                 │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ [🔄 Run Job Radar]              │ │  ← Manual trigger
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 3. Profile View (`/profile`)

**Agents:**
- **Resume Optimizer** - ATS optimization and improvement suggestions
- **Skill Gap Analysis** - Overall market skill assessment
- **Network Intelligence** - Connection opportunities

**UI Components:**
```
┌─────────────────────────────────────┐
│ Your Profile                        │
├─────────────────────────────────────┤
│ Resume                              │
│ ┌─────────────────────────────────┐ │
│ │ resume.pdf                      │ │
│ │ ATS Score: 72/100               │ │  ← Resume Optimizer
│ │ [Optimize for ATS]              │ │
│ └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│ Skills                              │
│ React, TypeScript, Node.js...       │
│ [Analyze Market Skill Gaps]         │  ← Skill Gap Agent
├─────────────────────────────────────┤
│ Network                             │
│ [Find Connection Opportunities]     │  ← Network Intelligence
└─────────────────────────────────────┘
```

### 4. Matches/Saved Jobs View (`/matches`)

**Agents:**
- **Application Tracker** - Daily briefing and follow-up reminders

**UI Components:**
```
┌─────────────────────────────────────┐
│ 📋 Daily Briefing                   │  ← Application Tracker Agent
│ • 2 applications need follow-up     │
│ • 1 interview scheduled tomorrow    │
│ • 3 new jobs match your profile     │
│ [View Full Briefing]                │
├─────────────────────────────────────┤
│ Saved Jobs (12)                     │
│ [Job Card - needs follow-up badge]  │
│ [Job Card]                          │
│ ...                                 │
└─────────────────────────────────────┘
```

---

## API Endpoints

All agents follow the async run/status/result pattern:

### Base Pattern
```
POST /agent/{agent}/run      → Returns { run_id, status: "running" }
GET  /agent/{agent}/status/{run_id}  → Returns { status, progress?, message? }
GET  /agent/{agent}/result/{run_id}  → Returns agent-specific result
```

### Endpoint Reference

| Agent | Run Endpoint | Request Body |
|-------|-------------|--------------|
| Job Radar | `POST /agent/radar/run` | `{ keywords?, profession?, remote_only?, min_score? }` |
| Interview Prep | `POST /agent/interview/prep` | `{ job_id, focus_areas? }` |
| Resume Optimizer | `POST /agent/resume/optimize` | `{ target_job_id? }` |
| Application Tracker | `POST /agent/tracker/briefing` | `{}` |
| Cover Letter | `POST /agent/cover-letter/generate` | `{ job_id, tone?, custom_instructions? }` |
| Salary Research | `POST /agent/salary/research` | `{ job_id?, title?, location?, skills? }` |
| Skill Gap | `POST /agent/skill-gap/analyze` | `{ job_id?, target_role? }` |
| Network Intelligence | `POST /agent/network/analyze` | `{ job_id?, company? }` |
| Auto-Apply | `POST /agent/apply/prepare` | `{ job_id }` |

---

## Implementation Phases

### Phase 1: Core Workflow (Priority)
1. **Cover Letter Generator** in Job Details
   - Already have proposal generation, extend to full cover letters
   - Primary CTA on job detail page

2. **Job Radar** in Jobs Feed
   - Replace or augment current job search
   - Pull-to-refresh integration

3. **Resume Optimizer** in Profile
   - Post-upload optimization suggestions
   - ATS score display

### Phase 2: Application Management
4. **Application Tracker** briefings
   - Daily summary card
   - Follow-up reminders

5. **Interview Prep** when status changes
   - Conditional UI based on match status

### Phase 3: Intelligence Features
6. **Salary Research** in Job Details
7. **Skill Gap Analysis** across views
8. **Network Intelligence** for target companies
9. **Auto-Apply** bundled application prep

---

## Shared Frontend Types

Add to `frontend/shared/src/types/index.ts`:

```typescript
// Agent run status
export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed';

// Generic agent run response
export interface AgentRunResponse {
  run_id: string;
  status: AgentRunStatus;
  message?: string;
}

// Generic agent status response
export interface AgentStatusResponse {
  status: AgentRunStatus;
  progress?: number;
  message?: string;
}

// Agent-specific result types
export interface JobRadarResult {
  jobs: ScoredJob[];
  total_found: number;
  sources_searched: string[];
}

export interface CoverLetterResult {
  content: string;
  tone: string;
  word_count: number;
  keywords_used: string[];
}

export interface ResumeOptimizeResult {
  score: number;
  suggestions: Array<{
    category: string;
    issue: string;
    fix: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  keywords_missing: string[];
  keywords_present: string[];
}

export interface InterviewPrepResult {
  questions: Array<{
    question: string;
    type: 'behavioral' | 'technical' | 'situational';
    tips: string[];
    sample_answer?: string;
  }>;
  company_research: {
    recent_news: string[];
    culture_notes: string[];
    interview_process?: string;
  };
}

export interface SalaryResearchResult {
  market_rate: {
    low: number;
    median: number;
    high: number;
  };
  factors: string[];
  negotiation_tips: string[];
  data_sources: string[];
}

export interface SkillGapResult {
  match_score: number;
  matched_skills: string[];
  missing_skills: Array<{
    skill: string;
    importance: 'required' | 'preferred';
    resources?: string[];
  }>;
  recommendations: string[];
}

export interface ApplicationTrackerResult {
  summary: {
    total_applications: number;
    pending_response: number;
    interviews_scheduled: number;
    needs_followup: number;
  };
  action_items: Array<{
    job_id: string;
    job_title: string;
    company: string;
    action: string;
    priority: 'high' | 'medium' | 'low';
    due_date?: string;
  }>;
  insights: string[];
}
```

---

## React Query Hooks Pattern

```typescript
// hooks/useAgent.ts
export function useAgentRun<TRequest, TResult>(
  agentName: string,
  options?: { onSuccess?: (result: TResult) => void }
) {
  const [runId, setRunId] = useState<string | null>(null);

  // Start agent run
  const runMutation = useMutation({
    mutationFn: (request: TRequest) =>
      api.post(`/agent/${agentName}/run`, request),
    onSuccess: (data) => setRunId(data.run_id),
  });

  // Poll status
  const statusQuery = useQuery({
    queryKey: ['agent', agentName, 'status', runId],
    queryFn: () => api.get(`/agent/${agentName}/status/${runId}`),
    enabled: !!runId,
    refetchInterval: (data) =>
      data?.status === 'running' ? 1000 : false,
  });

  // Fetch result when complete
  const resultQuery = useQuery({
    queryKey: ['agent', agentName, 'result', runId],
    queryFn: () => api.get(`/agent/${agentName}/result/${runId}`),
    enabled: statusQuery.data?.status === 'completed',
  });

  return {
    run: runMutation.mutate,
    isRunning: statusQuery.data?.status === 'running',
    progress: statusQuery.data?.progress,
    result: resultQuery.data,
    error: runMutation.error || statusQuery.error || resultQuery.error,
    reset: () => setRunId(null),
  };
}

// Usage
const { run, isRunning, result } = useAgentRun<
  CoverLetterRequest,
  CoverLetterResult
>('cover-letter');

// Trigger
run({ job_id: jobId, tone: 'professional' });
```

---

## Notes

- All agents require authentication (`requiresAuth: true`)
- Agent runs are stored in-memory (production: use Redis/database)
- Polling interval: 1 second while running
- Consider WebSocket upgrade for real-time status updates
- Mobile: Use React Native's AppState to pause polling when backgrounded
