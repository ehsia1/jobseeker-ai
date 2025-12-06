'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Briefcase, Search, Target, Zap, Users, BarChart3 } from 'lucide-react';
import { apiClient } from '@/lib/api/client';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dashboard if already authenticated
    if (apiClient.isAuthenticated()) {
      router.push('/dashboard');
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Briefcase className="h-8 w-8 text-primary" />
            <span className="text-2xl font-bold">JobSeeker AI</span>
          </div>
          <div className="space-x-2">
            <Button variant="ghost" asChild>
              <Link href="/login">Login</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get Started</Link>
            </Button>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <Badge variant="secondary" className="mb-4">
          AI-Powered Job Matching
        </Badge>
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
          Find Your Perfect
          <span className="text-primary block">Job Match</span>
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
          Let AI search thousands of job boards, analyze your skills, and deliver 
          personalized job recommendations with intelligent matching scores.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" asChild>
            <Link href="/register">Start Finding Jobs</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/demo">View Demo</Link>
          </Button>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            How JobSeeker AI Works
          </h2>
          <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Our intelligent agent works around the clock to find and score job opportunities 
            that match your unique profile.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Search className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Smart Job Discovery</CardTitle>
              <CardDescription>
                Search across 20+ job boards including RemoteOK, HackerNews, GitHub, 
                LinkedIn, and more simultaneously.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Target className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>AI-Powered Scoring</CardTitle>
              <CardDescription>
                Advanced 7-factor scoring algorithm analyzes skill match, experience, 
                compensation, location, and more.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Zap className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Automated Proposals</CardTitle>
              <CardDescription>
                Generate personalized cover letters and proposals tailored to each 
                job opportunity automatically.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Users className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>26+ Professions</CardTitle>
              <CardDescription>
                Support for software engineers, designers, marketers, sales, finance, 
                healthcare, and many more professions.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Real-time Analytics</CardTitle>
              <CardDescription>
                Track your job search progress with detailed analytics and insights 
                into market trends and opportunities.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                <Briefcase className="w-6 h-6 text-primary" />
              </div>
              <CardTitle>Smart Notifications</CardTitle>
              <CardDescription>
                Get notified instantly when high-scoring job matches are found 
                that fit your criteria and preferences.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Stats Section */}
      <section className="container mx-auto px-4 py-20 bg-white/50 dark:bg-gray-800/50 rounded-xl mx-4 mb-20">
        <div className="grid md:grid-cols-3 gap-8 text-center">
          <div>
            <div className="text-4xl font-bold text-primary mb-2">20+</div>
            <div className="text-lg text-gray-600 dark:text-gray-300">Job Boards</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-primary mb-2">95%</div>
            <div className="text-lg text-gray-600 dark:text-gray-300">Match Accuracy</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-primary mb-2">24/7</div>
            <div className="text-lg text-gray-600 dark:text-gray-300">AI Agent Active</div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-6">
          Ready to Find Your Dream Job?
        </h2>
        <p className="text-lg text-gray-600 dark:text-gray-300 mb-8 max-w-xl mx-auto">
          Join thousands of professionals who have found better opportunities with 
          AI-powered job matching.
        </p>
        <Button size="lg" asChild>
          <Link href="/register">Get Started Free</Link>
        </Button>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 border-t">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Briefcase className="h-5 w-5 text-primary" />
            <span className="font-semibold">JobSeeker AI</span>
          </div>
          <div className="text-sm text-gray-500">
            © 2024 JobSeeker AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
