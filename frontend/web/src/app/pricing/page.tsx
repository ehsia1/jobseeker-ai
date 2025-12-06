'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { PricingResponse, SubscriptionTier, TierInfo } from '@/lib/types';
import PricingCard from '@/components/features/PricingCard';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ArrowLeft, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export default function PricingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<SubscriptionTier | null>(null);
  const [pricing, setPricing] = useState<PricingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchPricing();

    // Check for success/cancel from Stripe redirect
    const params = new URLSearchParams(window.location.search);
    if (params.get('success') === 'true') {
      setSuccess('Payment successful! Your subscription has been upgraded.');
      // Clear the URL params
      router.replace('/pricing');
    } else if (params.get('canceled') === 'true') {
      setError('Payment was canceled. No changes were made to your subscription.');
      router.replace('/pricing');
    }
  }, [router]);

  const fetchPricing = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getPricing();
      setPricing(data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load pricing');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTier = async (tier: SubscriptionTier) => {
    if (tier === 'free') {
      // Handle downgrade to free - might need confirmation
      toast.info('To downgrade to free, please manage your subscription in the billing portal.');
      return;
    }

    try {
      setCheckoutLoading(tier);
      setError(null);

      const successUrl = `${window.location.origin}/pricing?success=true`;
      const cancelUrl = `${window.location.origin}/pricing?canceled=true`;

      const response = await apiClient.createCheckoutSession(tier, successUrl, cancelUrl);

      // Redirect to Stripe Checkout
      window.location.href = response.checkout_url;
    } catch (err: any) {
      const message = err.response?.data?.message || err.response?.data?.detail || 'Failed to create checkout session';
      setError(message);
      toast.error(message);
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleManageSubscription = async () => {
    try {
      const returnUrl = `${window.location.origin}/pricing`;
      const response = await apiClient.createPortalSession(returnUrl);
      window.location.href = response.portal_url;
    } catch (err: any) {
      toast.error('Failed to open billing portal');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="flex items-center mb-8">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>

        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Choose Your Plan</h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Supercharge your job search with AI-powered proposals and unlimited access to our tools.
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <Alert variant="destructive" className="max-w-2xl mx-auto mb-8">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert className="max-w-2xl mx-auto mb-8 border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertTitle className="text-green-800">Success</AlertTitle>
            <AlertDescription className="text-green-700">{success}</AlertDescription>
          </Alert>
        )}

        {/* Pricing Cards */}
        {pricing && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto mb-12">
            {pricing.tiers.map((tier) => (
              <PricingCard
                key={tier.id}
                tier={tier}
                currentTier={pricing.current_tier || undefined}
                onSelect={handleSelectTier}
                loading={checkoutLoading === tier.id}
              />
            ))}
          </div>
        )}

        {/* Manage Subscription */}
        {pricing?.current_tier && pricing.current_tier !== 'free' && (
          <div className="text-center">
            <Button variant="outline" onClick={handleManageSubscription}>
              Manage Subscription & Billing
            </Button>
          </div>
        )}

        {/* FAQ or Additional Info */}
        <div className="max-w-3xl mx-auto mt-16">
          <h2 className="text-2xl font-bold text-center mb-8">Frequently Asked Questions</h2>

          <div className="space-y-6">
            <div className="bg-card rounded-lg p-6">
              <h3 className="font-semibold mb-2">What happens when I hit my limit?</h3>
              <p className="text-muted-foreground">
                You'll see a friendly message letting you know you've reached your limit for the period.
                You can upgrade your plan at any time to continue using the features.
              </p>
            </div>

            <div className="bg-card rounded-lg p-6">
              <h3 className="font-semibold mb-2">Can I cancel anytime?</h3>
              <p className="text-muted-foreground">
                Yes! You can cancel your subscription at any time. You'll continue to have access
                until the end of your current billing period.
              </p>
            </div>

            <div className="bg-card rounded-lg p-6">
              <h3 className="font-semibold mb-2">When do limits reset?</h3>
              <p className="text-muted-foreground">
                Monthly limits (proposals, JD parses) reset on the same day each month when you subscribed.
                Daily limits (job searches) reset at midnight UTC.
              </p>
            </div>

            <div className="bg-card rounded-lg p-6">
              <h3 className="font-semibold mb-2">What payment methods do you accept?</h3>
              <p className="text-muted-foreground">
                We accept all major credit cards through Stripe, including Visa, Mastercard,
                American Express, and more. All payments are secure and encrypted.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
