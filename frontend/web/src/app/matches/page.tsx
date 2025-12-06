'use client';

import { useState } from 'react';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import AppLayout from '@/components/layout/AppLayout';
import ScoreBreakdown from '@/components/features/ScoreBreakdown';
import KanbanBoard from '@/components/features/KanbanBoard';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Search,
  Filter,
  Target,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  Bookmark,
  ExternalLink,
  Loader2,
  AlertCircle,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  LayoutList,
  Kanban,
} from 'lucide-react';
import { useJobMatches } from '@/hooks/useAPI';
import { apiClient } from '@/lib/api/client';
import { JobMatch, JobMatchStatus, ScoredJob } from '@/lib/types';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

type MatchStatus = 'all' | 'pending' | 'viewed' | 'applied' | 'saved' | 'rejected';
type SortBy = 'score' | 'date' | 'salary';
type ViewMode = 'list' | 'kanban';

export default function MatchesPage() {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const { matches, loading, error, pagination, refresh } = useJobMatches(undefined, currentPage, pageSize);
  
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);
  const [statusFilter, setStatusFilter] = useState<MatchStatus>('all');
  const [sortBy, setSortBy] = useState<SortBy>('score');
  const [searchQuery, setSearchQuery] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  // Filter and sort matches
  const filteredMatches = matches
    .filter(match => {
      if (statusFilter !== 'all' && match.status !== statusFilter) {
        return false;
      }
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          match.job.title.toLowerCase().includes(query) ||
          match.job.company.toLowerCase().includes(query) ||
          match.job.description?.toLowerCase().includes(query)
        );
      }
      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return b.total_score - a.total_score;
        case 'date':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'salary':
          const aSalary = a.job.rate_max || a.job.rate_min || 0;
          const bSalary = b.job.rate_max || b.job.rate_min || 0;
          return bSalary - aSalary;
        default:
          return 0;
      }
    });

  const updateMatchStatus = async (matchId: string, status: string) => {
    setUpdatingStatus(matchId);
    try {
      await apiClient.updateJobMatchStatus(matchId, status);
      toast.success(`Match ${status === 'applied' ? 'marked as applied' : status}`);
      refresh();
    } catch (err) {
      toast.error('Failed to update match status');
    } finally {
      setUpdatingStatus(null);
    }
  };

  const handleApply = async (match: JobMatch) => {
    // Open job URL in new tab
    window.open(match.job.url, '_blank');
    // Mark as applied
    await updateMatchStatus(match.id, 'applied');
  };

  const handleSave = async (match: JobMatch) => {
    const newStatus = match.status === 'saved' ? 'pending' : 'saved';
    await updateMatchStatus(match.id, newStatus);
  };

  const handleReject = async (match: JobMatch) => {
    await updateMatchStatus(match.id, 'rejected');
  };

  // Kanban handlers
  const handleKanbanStatusChange = async (matchId: string, status: JobMatchStatus) => {
    await updateMatchStatus(matchId, status);
  };

  const handleKanbanNotesChange = async (matchId: string, notes: string) => {
    try {
      await apiClient.updateJobMatchNotes(matchId, notes);
      refresh();
    } catch (err) {
      throw err; // Let KanbanBoard handle the error toast
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'applied':
        return <Badge className="bg-green-100 text-green-800">Applied</Badge>;
      case 'saved':
        return <Badge className="bg-blue-100 text-blue-800">Saved</Badge>;
      case 'rejected':
        return <Badge className="bg-red-100 text-red-800">Rejected</Badge>;
      case 'viewed':
        return <Badge className="bg-gray-100 text-gray-800">Viewed</Badge>;
      default:
        return <Badge>New</Badge>;
    }
  };

  const stats = {
    total: matches.length,
    pending: matches.filter(m => m.status === 'pending').length,
    applied: matches.filter(m => m.status === 'applied').length,
    saved: matches.filter(m => m.status === 'saved').length,
    avgScore: matches.length > 0 
      ? Math.round(matches.reduce((acc, m) => acc + m.total_score, 0) / matches.length)
      : 0
  };

  if (loading && matches.length === 0) {
    return (
      <ProtectedRoute requireProfile>
        <AppLayout>
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="mt-4 text-gray-600">Loading your job matches...</p>
            </div>
          </div>
        </AppLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute requireProfile>
      <AppLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">
                <Target className="h-8 w-8 text-primary" />
                Your Job Matches
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                AI-powered job matches based on your profile and preferences
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* View Toggle */}
              <div className="flex items-center border rounded-lg p-1">
                <Button
                  variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                  className="px-3"
                >
                  <LayoutList className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'kanban' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('kanban')}
                  className="px-3"
                >
                  <Kanban className="w-4 h-4" />
                </Button>
              </div>
              <Button className="flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Find New Matches
              </Button>
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Matches</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total}</div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>New Matches</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">{stats.pending}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Applied</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">{stats.applied}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Saved</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">{stats.saved}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg. Score</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-600">{stats.avgScore}%</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters and Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search matches..."
                    className="pl-9"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                
                <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as MatchStatus)}>
                  <SelectTrigger className="w-[180px]">
                    <Filter className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Matches</SelectItem>
                    <SelectItem value="pending">New</SelectItem>
                    <SelectItem value="saved">Saved</SelectItem>
                    <SelectItem value="applied">Applied</SelectItem>
                    <SelectItem value="rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortBy)}>
                  <SelectTrigger className="w-[180px]">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="score">Match Score</SelectItem>
                    <SelectItem value="date">Date Added</SelectItem>
                    <SelectItem value="salary">Salary</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {filteredMatches.length === 0 ? (
            <Card className="py-12">
              <CardContent className="text-center">
                <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">
                  {searchQuery || statusFilter !== 'all'
                    ? 'No matches found with current filters'
                    : 'No job matches yet'
                  }
                </h3>
                <p className="text-gray-600 mb-4">
                  {searchQuery || statusFilter !== 'all'
                    ? 'Try adjusting your filters'
                    : 'Run the AI agent to find job matches'
                  }
                </p>
                <Button>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Find Job Matches
                </Button>
              </CardContent>
            </Card>
          ) : viewMode === 'kanban' ? (
            <KanbanBoard
              matches={matches}
              onStatusChange={handleKanbanStatusChange}
              onNotesChange={handleKanbanNotesChange}
              loading={loading}
            />
          ) : (
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Job List */}
              <div className="space-y-4">
                <h3 className="font-semibold text-lg">
                  {filteredMatches.length} {filteredMatches.length === 1 ? 'Match' : 'Matches'} Found
                </h3>
                
                {filteredMatches.map((match) => {
                  const scoredJob: ScoredJob = {
                    ...match.job,
                    total_score: match.total_score,
                    score_breakdown: match.score_breakdown as ScoredJob['score_breakdown'],
                    explanation: match.explanation,
                    recommended: match.total_score >= 70
                  };

                  return (
                    <div 
                      key={match.id} 
                      className={`cursor-pointer transition-all ${
                        selectedMatch?.id === match.id ? 'ring-2 ring-primary' : ''
                      }`}
                      onClick={() => setSelectedMatch(match)}
                    >
                      <Card className="hover:shadow-lg transition-shadow">
                        <CardContent className="pt-6">
                          <div className="flex justify-between items-start mb-4">
                            <div className="flex-1">
                              <h4 className="font-semibold text-lg">{match.job.title}</h4>
                              <p className="text-gray-600">{match.job.company}</p>
                            </div>
                            <div className="flex flex-col items-end gap-2">
                              {getStatusBadge(match.status)}
                              <Badge variant="outline" className="font-bold">
                                {Math.round(match.total_score)}% match
                              </Badge>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-2 mb-4">
                            {match.job.remote && (
                              <Badge variant="secondary">Remote</Badge>
                            )}
                            {match.job.location && (
                              <Badge variant="secondary">{match.job.location}</Badge>
                            )}
                            <Badge variant="secondary">
                              {formatDistanceToNow(new Date(match.job.posted_at), { addSuffix: true })}
                            </Badge>
                          </div>

                          <ScoreBreakdown
                            totalScore={match.total_score}
                            breakdown={match.score_breakdown}
                            compact
                          />

                          <div className="flex gap-2 mt-4">
                            {match.status !== 'applied' && (
                              <Button 
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleApply(match);
                                }}
                                disabled={updatingStatus === match.id}
                              >
                                Apply Now
                              </Button>
                            )}
                            
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSave(match);
                              }}
                              disabled={updatingStatus === match.id}
                            >
                              {match.status === 'saved' ? (
                                <>
                                  <Bookmark className="w-4 h-4 mr-1 fill-current" />
                                  Saved
                                </>
                              ) : (
                                <>
                                  <Bookmark className="w-4 h-4 mr-1" />
                                  Save
                                </>
                              )}
                            </Button>

                            {match.status !== 'rejected' && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleReject(match);
                                }}
                                disabled={updatingStatus === match.id}
                              >
                                <XCircle className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  );
                })}

                {/* Pagination */}
                {pagination.pages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      Previous
                    </Button>
                    <span className="text-sm text-gray-600">
                      Page {currentPage} of {pagination.pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(Math.min(pagination.pages, currentPage + 1))}
                      disabled={currentPage === pagination.pages}
                    >
                      Next
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                )}
              </div>

              {/* Selected Match Details */}
              <div className="space-y-4">
                {selectedMatch ? (
                  <>
                    <Card>
                      <CardHeader>
                        <CardTitle>{selectedMatch.job.title}</CardTitle>
                        <CardDescription className="flex items-center justify-between">
                          <span>{selectedMatch.job.company}</span>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => window.open(selectedMatch.job.url, '_blank')}
                          >
                            <ExternalLink className="w-4 h-4 mr-1" />
                            View Original
                          </Button>
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <h4 className="font-semibold mb-2">Description</h4>
                          <p className="text-sm text-gray-600 whitespace-pre-wrap">
                            {selectedMatch.job.description}
                          </p>
                        </div>

                        {selectedMatch.job.skills && selectedMatch.job.skills.length > 0 && (
                          <div>
                            <h4 className="font-semibold mb-2">Required Skills</h4>
                            <div className="flex flex-wrap gap-2">
                              {selectedMatch.job.skills.map((skill, idx) => (
                                <Badge key={idx} variant="secondary">
                                  {skill}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-2 gap-4 text-sm">
                          {selectedMatch.job.rate_min && (
                            <div>
                              <span className="text-gray-600">Salary Range:</span>
                              <p className="font-medium">
                                ${selectedMatch.job.rate_min.toLocaleString()} - 
                                ${selectedMatch.job.rate_max?.toLocaleString() || '∞'}
                              </p>
                            </div>
                          )}
                          <div>
                            <span className="text-gray-600">Employment Type:</span>
                            <p className="font-medium">
                              {selectedMatch.job.employment_type || 'Full-time'}
                            </p>
                          </div>
                          <div>
                            <span className="text-gray-600">Posted:</span>
                            <p className="font-medium">
                              {formatDistanceToNow(new Date(selectedMatch.job.posted_at), { addSuffix: true })}
                            </p>
                          </div>
                          <div>
                            <span className="text-gray-600">Source:</span>
                            <p className="font-medium">{selectedMatch.job.source}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <ScoreBreakdown
                      totalScore={selectedMatch.total_score}
                      breakdown={selectedMatch.score_breakdown}
                      explanation={selectedMatch.explanation}
                    />
                  </>
                ) : (
                  <Card className="h-full flex items-center justify-center">
                    <CardContent className="text-center py-12">
                      <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium mb-2">Select a match to view details</h3>
                      <p className="text-sm text-gray-600">
                        Click on any job match to see full details and score analysis
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          )}
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}