'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import AppLayout from '@/components/layout/AppLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Briefcase,
  Search,
  Target,
  TrendingUp,
  Bell,
  ExternalLink,
  Sparkles,
  Loader2,
  CheckCircle
} from 'lucide-react';
import { useCurrentUser, useUserProfile, useJobMatches, useUsageStats } from '@/hooks/useAPI';
import UsageDisplay from '@/components/features/UsageDisplay';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: userLoading } = useCurrentUser();
  const { profile } = useUserProfile();
  const { matches, loading: matchesLoading, refresh: refreshMatches } = useJobMatches(undefined, 1, 5);
  const { usage, loading: usageLoading } = useUsageStats();
  const [runningAgent, setRunningAgent] = useState(false);
  const [agentResult, setAgentResult] = useState<{ matches_found?: number; top_matches?: Array<{ id: string }>; source_stats?: Record<string, number> } | null>(null);

  const getProfileCompletionScore = () => {
    if (!profile) return 0;
    let score = 0;
    if (profile.profession) score += 20;
    if (profile.skills?.length > 0) score += 20;
    if (profile.experience) score += 20;
    if (profile.location) score += 15;
    if (profile.min_rate_usd) score += 15;
    if (profile.preferences) score += 10;
    return Math.min(score, 100);
  };

  const profileScore = getProfileCompletionScore();

  const runJobAgent = async () => {
    if (!profile || profileScore < 50) {
      toast.error('Please complete your profile first (at least 50%)');
      router.push('/profile');
      return;
    }

    setRunningAgent(true);
    setAgentResult(null);

    try {
      toast.info('AI Agent starting job search across multiple boards...');
      
      const result = await apiClient.runJobRadarAgent(
        user?.id,
        profile.skills,
        profile.profession
      );

      if (result.success) {
        setAgentResult(result);
        toast.success(`Found ${result.matches_found} new job matches!`);
        
        // Refresh matches after a short delay
        setTimeout(() => {
          refreshMatches();
        }, 1000);

        // Navigate to matches page if many found
        if (result.matches_found > 5) {
          setTimeout(() => {
            router.push('/matches');
          }, 2000);
        }
      } else {
        toast.error('Agent failed to find matches. Please try again.');
      }
    } catch (err) {
      console.error('Agent error:', err);
      toast.error((err as Error)?.message || 'Failed to run job search agent');
    } finally {
      setRunningAgent(false);
    }
  };

  if (userLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Welcome Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Welcome back, {user?.full_name || 'there'}! 👋
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-2">
              Here&apos;s your job search overview and latest opportunities.
            </p>
          </div>
          <Button 
            onClick={runJobAgent}
            disabled={runningAgent || profileScore < 50}
          >
            {runningAgent ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                Run AI Agent
              </>
            )}
          </Button>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Job Matches</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{matches.length}</div>
              <p className="text-xs text-muted-foreground">
                +12% from last week
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Profile Score</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{profileScore}%</div>
              <Progress value={profileScore} className="mt-2" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Applications</CardTitle>
              <Briefcase className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">8</div>
              <p className="text-xs text-muted-foreground">
                3 pending responses
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <Search className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">75%</div>
              <p className="text-xs text-muted-foreground">
                Above average
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Agent Result Alert */}
        {agentResult && (
          <Alert className="bg-green-50 border-green-200">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              <strong>AI Agent Complete!</strong> Found {agentResult.matches_found} job matches across {Object.keys(agentResult.source_stats || {}).length} job boards.
              {(agentResult.matches_found ?? 0) > 0 && (
                <Button 
                  variant="link" 
                  className="ml-2 p-0 h-auto text-green-700"
                  onClick={() => router.push('/matches')}
                >
                  View Matches →
                </Button>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Profile Completion Alert */}
        {profileScore < 80 && !runningAgent && (
          <Card className="border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950">
            <CardHeader>
              <CardTitle className="text-orange-800 dark:text-orange-200 flex items-center">
                <Bell className="w-5 h-5 mr-2" />
                Complete Your Profile
              </CardTitle>
              <CardDescription className="text-orange-700 dark:text-orange-300">
                Your profile is {profileScore}% complete. Complete it to get better job matches.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                variant="outline" 
                className="border-orange-300 text-orange-800 hover:bg-orange-100"
                onClick={() => router.push('/profile')}
              >
                Complete Profile
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Recent Job Matches */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Job Matches</CardTitle>
              <CardDescription>
                Latest opportunities found by your AI agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              {matchesLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : matches.length > 0 ? (
                <div className="space-y-4">
                  {matches.slice(0, 3).map((match) => (
                    <div key={match.id} className="flex items-start justify-between border-b pb-4 last:border-b-0">
                      <div className="flex-1">
                        <h4 className="font-medium">{match.job.title}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {match.job.company}
                        </p>
                        <div className="flex items-center mt-2 space-x-2">
                          <Badge variant="secondary">
                            {Math.round(match.total_score)}% match
                          </Badge>
                          {match.job.remote && (
                            <Badge variant="outline">Remote</Badge>
                          )}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                  <Button variant="outline" className="w-full">
                    View All Matches
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="font-medium text-gray-900 dark:text-white mb-2">
                    No matches yet
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    Run the AI agent to find job opportunities
                  </p>
                  <Button>
                    Start Job Search
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Usage Stats */}
          {usage && !usageLoading ? (
            <UsageDisplay usage={usage} compact />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Usage Stats</CardTitle>
                <CardDescription>
                  Your subscription usage this period
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-2 bg-gray-200 rounded w-full"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-2 bg-gray-200 rounded w-full"></div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks to improve your job search
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              <Button variant="outline" className="flex flex-col h-20">
                <Search className="w-5 h-5 mb-1" />
                <span className="text-sm">Search Jobs</span>
              </Button>
              
              <Button variant="outline" className="flex flex-col h-20">
                <Target className="w-5 h-5 mb-1" />
                <span className="text-sm">Run AI Agent</span>
              </Button>
              
              <Button variant="outline" className="flex flex-col h-20">
                <Briefcase className="w-5 h-5 mb-1" />
                <span className="text-sm">Update Profile</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}