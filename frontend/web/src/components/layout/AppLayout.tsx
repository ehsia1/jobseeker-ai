'use client';

import { ReactNode } from 'react';
import Navbar from './Navbar';
import { Toaster } from '@/components/ui/sonner';
import { useHealthCheck } from '@/hooks/useAPI';
import { AlertTriangle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { healthy, loading: healthLoading } = useHealthCheck();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      {/* Health Status Alert */}
      {!healthLoading && !healthy && (
        <Alert variant="destructive" className="m-4 max-w-7xl mx-auto">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Backend service is unavailable. Some features may not work properly.
          </AlertDescription>
        </Alert>
      )}
      
      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 max-w-7xl">
        {children}
      </main>
      
      {/* Toast Notifications */}
      <Toaster />
    </div>
  );
}