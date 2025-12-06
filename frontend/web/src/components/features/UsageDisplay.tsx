'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  FileText,
  Search,
  FileCode,
  Calendar,
  ArrowUpRight,
  Infinity,
  AlertTriangle
} from 'lucide-react';
import { UsageStats, SubscriptionTier } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

interface UsageDisplayProps {
  usage: UsageStats;
  compact?: boolean;
  showUpgrade?: boolean;
}

export default function UsageDisplay({
  usage,
  compact = false,
  showUpgrade = true
}: UsageDisplayProps) {
  const getTierColor = (tier: SubscriptionTier): string => {
    const colors: Record<SubscriptionTier, string> = {
      free: 'bg-gray-100 text-gray-800',
      starter: 'bg-blue-100 text-blue-800',
      pro: 'bg-purple-100 text-purple-800',
      power: 'bg-gradient-to-r from-amber-400 to-orange-500 text-white',
    };
    return colors[tier];
  };

  const getUsagePercentage = (used: number, limit: number): number => {
    if (limit === -1) return 0; // Unlimited
    return Math.min((used / limit) * 100, 100);
  };

  const getUsageColor = (percentage: number): string => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-amber-500';
    return 'bg-primary';
  };

  const formatUsage = (used: number, limit: number): string => {
    if (limit === -1) return `${used} used`;
    return `${used} / ${limit}`;
  };

  const isNearLimit = (used: number, limit: number): boolean => {
    if (limit === -1) return false;
    return (used / limit) >= 0.9;
  };

  if (compact) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Plan:</span>
              <Badge className={getTierColor(usage.tier)}>
                {usage.tier.charAt(0).toUpperCase() + usage.tier.slice(1)}
              </Badge>
            </div>
            {showUpgrade && usage.tier !== 'power' && (
              <Link href="/pricing">
                <Button variant="ghost" size="sm">
                  Upgrade <ArrowUpRight className="w-3 h-3 ml-1" />
                </Button>
              </Link>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3 text-center text-sm">
            <div>
              <div className="text-muted-foreground">Proposals</div>
              <div className="font-medium">
                {usage.proposals_remaining === -1 ? (
                  <Infinity className="w-4 h-4 inline" />
                ) : (
                  usage.proposals_remaining
                )}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">JD Parses</div>
              <div className="font-medium">
                {usage.jd_parses_remaining === -1 ? (
                  <Infinity className="w-4 h-4 inline" />
                ) : (
                  usage.jd_parses_remaining
                )}
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Searches</div>
              <div className="font-medium">
                {usage.job_searches_remaining_today === -1 ? (
                  <Infinity className="w-4 h-4 inline" />
                ) : (
                  usage.job_searches_remaining_today
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              Usage & Limits
              <Badge className={getTierColor(usage.tier)}>
                {usage.tier.charAt(0).toUpperCase() + usage.tier.slice(1)}
              </Badge>
            </CardTitle>
            <CardDescription className="mt-1">
              {usage.monthly_reset_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  Resets {formatDistanceToNow(new Date(usage.monthly_reset_date), { addSuffix: true })}
                </span>
              )}
            </CardDescription>
          </div>
          {showUpgrade && usage.tier !== 'power' && (
            <Link href="/pricing">
              <Button>
                Upgrade Plan <ArrowUpRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Proposals */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-muted-foreground" />
              <span className="font-medium">Proposals</span>
              {isNearLimit(usage.proposals_used, usage.proposals_limit) && (
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              )}
            </div>
            <span className="text-sm text-muted-foreground">
              {usage.proposals_limit === -1 ? (
                <span className="flex items-center gap-1">
                  <Infinity className="w-4 h-4" /> Unlimited
                </span>
              ) : (
                formatUsage(usage.proposals_used, usage.proposals_limit)
              )}
            </span>
          </div>
          {usage.proposals_limit !== -1 && (
            <Progress
              value={getUsagePercentage(usage.proposals_used, usage.proposals_limit)}
              className="h-2"
            />
          )}
        </div>

        {/* JD Parses */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-muted-foreground" />
              <span className="font-medium">JD Parses</span>
              {isNearLimit(usage.jd_parses_used, usage.jd_parses_limit) && (
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              )}
            </div>
            <span className="text-sm text-muted-foreground">
              {usage.jd_parses_limit === -1 ? (
                <span className="flex items-center gap-1">
                  <Infinity className="w-4 h-4" /> Unlimited
                </span>
              ) : (
                formatUsage(usage.jd_parses_used, usage.jd_parses_limit)
              )}
            </span>
          </div>
          {usage.jd_parses_limit !== -1 && (
            <Progress
              value={getUsagePercentage(usage.jd_parses_used, usage.jd_parses_limit)}
              className="h-2"
            />
          )}
        </div>

        {/* Job Searches (Daily) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-muted-foreground" />
              <span className="font-medium">Job Searches</span>
              <Badge variant="outline" className="text-xs">Today</Badge>
              {isNearLimit(usage.job_searches_used_today, usage.job_searches_limit_daily) && (
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              )}
            </div>
            <span className="text-sm text-muted-foreground">
              {usage.job_searches_limit_daily === -1 ? (
                <span className="flex items-center gap-1">
                  <Infinity className="w-4 h-4" /> Unlimited
                </span>
              ) : (
                formatUsage(usage.job_searches_used_today, usage.job_searches_limit_daily)
              )}
            </span>
          </div>
          {usage.job_searches_limit_daily !== -1 && (
            <Progress
              value={getUsagePercentage(usage.job_searches_used_today, usage.job_searches_limit_daily)}
              className="h-2"
            />
          )}
          {usage.daily_reset_date && (
            <p className="text-xs text-muted-foreground">
              Resets daily at midnight
            </p>
          )}
        </div>

        {/* Available Features */}
        <div className="pt-4 border-t">
          <h4 className="font-medium mb-3">Available Features</h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-2">
              <Badge variant={usage.features.proposal_enhance ? 'default' : 'secondary'}>
                {usage.features.proposal_enhance ? 'Yes' : 'No'}
              </Badge>
              <span>Proposal Enhancement</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={usage.features.analytics ? 'default' : 'secondary'}>
                {usage.features.analytics ? 'Yes' : 'No'}
              </Badge>
              <span>Analytics</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={usage.features.auto_apply ? 'default' : 'secondary'}>
                {usage.features.auto_apply ? 'Yes' : 'No'}
              </Badge>
              <span>Auto-Apply</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={usage.features.priority_support ? 'default' : 'secondary'}>
                {usage.features.priority_support ? 'Yes' : 'No'}
              </Badge>
              <span>Priority Support</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
