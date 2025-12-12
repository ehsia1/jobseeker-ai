'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  MapPin,
  DollarSign,
  Clock,
  Building2,
  ExternalLink,
  Calendar,
  TrendingUp,
  FileText,
  Briefcase,
} from 'lucide-react';
import { Job, ScoredJob } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';

interface JobDetailsModalProps {
  job: Job | ScoredJob;
  open: boolean;
  onClose: () => void;
  onGenerateProposal: () => void;
  onApply: () => void;
}

export default function JobDetailsModal({
  job,
  open,
  onClose,
  onGenerateProposal,
  onApply,
}: JobDetailsModalProps) {
  const isScoredJob = (job: Job | ScoredJob): job is ScoredJob => {
    return 'total_score' in job;
  };

  const formatSalary = () => {
    if (!job.rate_min && !job.rate_max) return null;

    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
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

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh]">
        <DialogHeader>
          <div className="flex justify-between items-start gap-4">
            <div>
              <DialogTitle className="text-xl">{job.title}</DialogTitle>
              <DialogDescription className="flex items-center gap-4 mt-2">
                <span className="flex items-center gap-1">
                  <Building2 className="w-4 h-4" />
                  {job.company}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {formatDistanceToNow(new Date(job.posted_at), { addSuffix: true })}
                </span>
              </DialogDescription>
            </div>
            {isScored && (
              <div className={`px-3 py-2 rounded-lg border ${getScoreColor(score)}`}>
                <div className="text-2xl font-bold">{score}%</div>
                <div className="text-xs">match</div>
              </div>
            )}
          </div>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-4">
          <div className="space-y-6">
            {/* Job Meta */}
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

            {/* Score Breakdown */}
            {isScored && job.score_breakdown && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Match Analysis
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <span className="text-gray-600 dark:text-gray-300">Skills Match</span>
                      <span className="font-medium">{Math.round(job.score_breakdown.skill_match)}%</span>
                    </div>
                    <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <span className="text-gray-600 dark:text-gray-300">Experience</span>
                      <span className="font-medium">{Math.round(job.score_breakdown.experience_match)}%</span>
                    </div>
                    <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <span className="text-gray-600 dark:text-gray-300">Compensation</span>
                      <span className="font-medium">{Math.round(job.score_breakdown.compensation_match)}%</span>
                    </div>
                    <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <span className="text-gray-600 dark:text-gray-300">Location</span>
                      <span className="font-medium">{Math.round(job.score_breakdown.location_match)}%</span>
                    </div>
                  </div>
                  {job.explanation && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 italic bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
                      {job.explanation}
                    </p>
                  )}
                </div>
              </>
            )}

            {/* Skills */}
            {job.skills && job.skills.length > 0 && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <Briefcase className="w-4 h-4" />
                    Required Skills
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {job.skills.map((skill, idx) => (
                      <Badge key={idx} variant="secondary">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Description */}
            <Separator />
            <div className="space-y-3">
              <h4 className="font-medium">Job Description</h4>
              <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {job.description}
              </div>
            </div>
          </div>
        </ScrollArea>

        {/* Actions */}
        <div className="flex gap-3 pt-4 border-t">
          <Button className="flex-1" onClick={onApply}>
            <ExternalLink className="w-4 h-4 mr-2" />
            Apply Now
          </Button>
          <Button variant="outline" className="flex-1" onClick={onGenerateProposal}>
            <FileText className="w-4 h-4 mr-2" />
            Generate Proposal
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
