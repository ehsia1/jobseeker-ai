'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  MapPin,
  DollarSign,
  Clock,
  Building2,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
  TrendingUp,
  Calendar,
  FileText
} from 'lucide-react';
import { Job, ScoredJob } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';

interface JobCardProps {
  job: Job | ScoredJob;
  onView?: (job: Job | ScoredJob) => void;
  onSave?: (job: Job | ScoredJob) => void;
  onApply?: (job: Job | ScoredJob) => void;
  onGenerateProposal?: (job: Job | ScoredJob) => void;
  isSaved?: boolean;
  showScore?: boolean;
  compact?: boolean;
}

export default function JobCard({
  job,
  onView,
  onSave,
  onApply,
  onGenerateProposal,
  isSaved = false,
  showScore = false,
  compact = false
}: JobCardProps) {
  const isScoredJob = (job: Job | ScoredJob): job is ScoredJob => {
    return 'total_score' in job;
  };

  const formatSalary = () => {
    if (!job.rate_min && !job.rate_max) return null;
    
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    });

    if (job.rate_min && job.rate_max) {
      return `${formatter.format(job.rate_min)} - ${formatter.format(job.rate_max)}`;
    } else if (job.rate_min) {
      return `From ${formatter.format(job.rate_min)}`;
    } else if (job.rate_max) {
      return `Up to ${formatter.format(job.rate_max)}`;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 60) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const salary = formatSalary();
  const isScored = isScoredJob(job);
  const score = isScored ? Math.round(job.total_score) : 0;

  if (compact) {
    return (
      <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => onView?.(job)}>
        <CardHeader className="pb-3">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <CardTitle className="text-lg line-clamp-1">{job.title}</CardTitle>
              <CardDescription className="flex items-center gap-2 mt-1">
                <Building2 className="w-3 h-3" />
                {job.company}
              </CardDescription>
            </div>
            {showScore && isScored && (
              <Badge className={getScoreColor(score)}>
                {score}% match
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-wrap gap-2">
            {job.remote && <Badge variant="secondary">Remote</Badge>}
            {job.location && (
              <Badge variant="outline">
                <MapPin className="w-3 h-3 mr-1" />
                {job.location}
              </Badge>
            )}
            {salary && (
              <Badge variant="outline">
                <DollarSign className="w-3 h-3 mr-1" />
                {job.rate_type || 'Yearly'}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <CardTitle className="text-xl">{job.title}</CardTitle>
            <CardDescription className="flex items-center gap-4 mt-2">
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {job.company}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {formatDistanceToNow(new Date(job.posted_at), { addSuffix: true })}
              </span>
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {showScore && isScored && (
              <div className={`px-3 py-2 rounded-lg border ${getScoreColor(score)}`}>
                <div className="text-2xl font-bold">{score}%</div>
                <div className="text-xs">match</div>
              </div>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                onSave?.(job);
              }}
            >
              {isSaved ? (
                <BookmarkCheck className="w-4 h-4 fill-current" />
              ) : (
                <Bookmark className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Job Details */}
        <div className="flex flex-wrap gap-3">
          {job.remote && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              Remote
            </Badge>
          )}
          {job.location && !job.remote && (
            <Badge variant="outline" className="flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {job.location}
            </Badge>
          )}
          {salary && (
            <Badge variant="outline" className="flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              {salary} {job.rate_type && `/ ${job.rate_type}`}
            </Badge>
          )}
          {job.employment_type && (
            <Badge variant="outline" className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {job.employment_type}
            </Badge>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
          {job.description}
        </p>

        {/* Skills */}
        {job.skills && job.skills.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Required Skills</h4>
            <div className="flex flex-wrap gap-2">
              {job.skills.slice(0, 6).map((skill, idx) => (
                <Badge key={idx} variant="secondary">
                  {skill}
                </Badge>
              ))}
              {job.skills.length > 6 && (
                <Badge variant="outline">+{job.skills.length - 6} more</Badge>
              )}
            </div>
          </div>
        )}

        {/* Score Breakdown */}
        {showScore && isScored && job.score_breakdown && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Match Analysis
            </h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Skills:</span>
                <span className="font-medium">{Math.round(job.score_breakdown.skill_match)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Experience:</span>
                <span className="font-medium">{Math.round(job.score_breakdown.experience_match)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Compensation:</span>
                <span className="font-medium">{Math.round(job.score_breakdown.compensation_match)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Location:</span>
                <span className="font-medium">{Math.round(job.score_breakdown.location_match)}%</span>
              </div>
            </div>
            {job.explanation && (
              <p className="text-xs text-gray-600 dark:text-gray-400 italic mt-2">
                {job.explanation}
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            className="flex-1"
            onClick={(e) => {
              e.stopPropagation();
              onApply?.(job);
            }}
          >
            Apply Now
          </Button>
          <Button
            variant="outline"
            onClick={(e) => {
              e.stopPropagation();
              onGenerateProposal?.(job);
            }}
          >
            <FileText className="w-4 h-4 mr-2" />
            Proposal
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              onView?.(job);
            }}
          >
            <ExternalLink className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}