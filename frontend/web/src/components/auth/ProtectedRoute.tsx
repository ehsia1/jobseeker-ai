'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCurrentUser } from '@/hooks/useAPI';
import { Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireProfile?: boolean;
}

export default function ProtectedRoute({ children, requireProfile = false }: ProtectedRouteProps) {
  const router = useRouter();
  const { user, loading, error } = useCurrentUser();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if user has token
    const hasToken = apiClient.isAuthenticated();
    
    if (!hasToken) {
      router.push('/login');
      return;
    }

    // If we have a token but error fetching user, token might be expired
    if (error && !loading) {
      apiClient.clearAuthToken();
      router.push('/login');
      return;
    }

    // User is authenticated
    if (user) {
      setIsAuthenticated(true);
      
      // Check if profile is required and redirect to onboarding if needed
      if (requireProfile) {
        checkUserProfile(user.id);
      }
    }
  }, [user, loading, error, router, requireProfile]);

  const checkUserProfile = async (userId: string) => {
    try {
      const response = await apiClient.getUserProfile();
      if (!response.data || !response.data.profession) {
        router.push('/onboarding');
      }
    } catch (err) {
      // No profile yet, redirect to onboarding
      router.push('/onboarding');
    }
  };

  // Show loading while checking authentication
  if (loading || isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // User is authenticated, render children
  return <>{children}</>;
}