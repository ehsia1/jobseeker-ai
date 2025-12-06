'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Check, X, Sparkles } from 'lucide-react';
import { TierInfo, SubscriptionTier } from '@/lib/types';

interface PricingCardProps {
  tier: TierInfo;
  currentTier?: SubscriptionTier;
  onSelect: (tier: SubscriptionTier) => void;
  loading?: boolean;
}

export default function PricingCard({
  tier,
  currentTier,
  onSelect,
  loading = false
}: PricingCardProps) {
  const isCurrentPlan = currentTier === tier.id;
  const isUpgrade = currentTier && getTierOrder(tier.id) > getTierOrder(currentTier);
  const isDowngrade = currentTier && getTierOrder(tier.id) < getTierOrder(currentTier);

  function getTierOrder(t: SubscriptionTier): number {
    const order: Record<SubscriptionTier, number> = {
      free: 0,
      starter: 1,
      pro: 2,
      power: 3,
    };
    return order[t];
  }

  const formatLimit = (limit: number): string => {
    if (limit === -1) return 'Unlimited';
    return limit.toString();
  };

  return (
    <Card className={`relative flex flex-col ${tier.popular ? 'border-2 border-primary shadow-lg scale-105' : ''}`}>
      {tier.popular && (
        <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1">
          <Sparkles className="w-3 h-3 mr-1" />
          Most Popular
        </Badge>
      )}

      <CardHeader className="text-center pb-4">
        <CardTitle className="text-2xl">{tier.name}</CardTitle>
        <CardDescription className="text-3xl font-bold mt-2">
          {tier.price_display}
          {tier.price_cents > 0 && (
            <span className="text-sm font-normal text-muted-foreground">/month</span>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 space-y-6">
        {/* Limits */}
        <div className="space-y-3">
          <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
            Monthly Limits
          </h4>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between">
              <span>Proposals</span>
              <span className="font-medium">{formatLimit(tier.limits.proposals_per_month)}</span>
            </li>
            <li className="flex justify-between">
              <span>JD Parses</span>
              <span className="font-medium">{formatLimit(tier.limits.jd_parses_per_month)}</span>
            </li>
            <li className="flex justify-between">
              <span>Job Searches/day</span>
              <span className="font-medium">{formatLimit(tier.limits.job_searches_per_day)}</span>
            </li>
            <li className="flex justify-between">
              <span>Resume Uploads</span>
              <span className="font-medium">{formatLimit(tier.limits.resume_uploads)}</span>
            </li>
          </ul>
        </div>

        {/* Features */}
        <div className="space-y-3">
          <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider">
            Features
          </h4>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center gap-2">
              {tier.limits.features.proposal_tones.length > 1 ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <X className="w-4 h-4 text-gray-300" />
              )}
              <span>
                {tier.limits.features.proposal_tones.length === 3
                  ? 'All proposal tones'
                  : tier.limits.features.proposal_tones.length === 2
                  ? 'Short & medium tones'
                  : 'Short tone only'}
              </span>
            </li>
            <li className="flex items-center gap-2">
              {tier.limits.features.proposal_enhance ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <X className="w-4 h-4 text-gray-300" />
              )}
              <span className={!tier.limits.features.proposal_enhance ? 'text-muted-foreground' : ''}>
                Proposal enhancement
              </span>
            </li>
            <li className="flex items-center gap-2">
              {tier.limits.features.analytics ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <X className="w-4 h-4 text-gray-300" />
              )}
              <span className={!tier.limits.features.analytics ? 'text-muted-foreground' : ''}>
                Advanced analytics
              </span>
            </li>
            <li className="flex items-center gap-2">
              {tier.limits.features.auto_apply ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <X className="w-4 h-4 text-gray-300" />
              )}
              <span className={!tier.limits.features.auto_apply ? 'text-muted-foreground' : ''}>
                Auto-apply automation
              </span>
            </li>
            <li className="flex items-center gap-2">
              {tier.limits.features.priority_support ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <X className="w-4 h-4 text-gray-300" />
              )}
              <span className={!tier.limits.features.priority_support ? 'text-muted-foreground' : ''}>
                Priority support
              </span>
            </li>
          </ul>
        </div>

        {/* Action Button */}
        <div className="pt-4">
          {isCurrentPlan ? (
            <Button className="w-full" variant="outline" disabled>
              Current Plan
            </Button>
          ) : tier.id === 'free' ? (
            <Button
              className="w-full"
              variant="outline"
              disabled={isDowngrade || loading}
              onClick={() => onSelect(tier.id)}
            >
              {isDowngrade ? 'Downgrade' : 'Get Started'}
            </Button>
          ) : (
            <Button
              className="w-full"
              variant={tier.popular ? 'default' : 'outline'}
              disabled={loading}
              onClick={() => onSelect(tier.id)}
            >
              {loading ? 'Processing...' : isUpgrade ? 'Upgrade Now' : 'Select Plan'}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
