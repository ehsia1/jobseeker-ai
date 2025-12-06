'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Briefcase, Mail, Lock, Loader2, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    remember: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await apiClient.login(formData.email, formData.password);
      
      if (response.access_token) {
        // Store token
        apiClient.setAuthToken(response.access_token);
        
        // Store in localStorage if remember me is checked
        if (formData.remember) {
          localStorage.setItem('remember_me', 'true');
        }
        
        toast.success('Welcome back!');
        
        // Redirect to dashboard
        router.push('/dashboard');
      }
    } catch (err) {
      const errorMessage = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Invalid email or password';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    // Demo login for testing - credentials from environment
    const demoEmail = process.env.NEXT_PUBLIC_DEMO_EMAIL;
    const demoPassword = process.env.NEXT_PUBLIC_DEMO_PASSWORD;

    if (demoEmail && demoPassword) {
      setFormData({
        email: demoEmail,
        password: demoPassword,
        remember: false,
      });
      toast.info('Demo credentials loaded');
    } else {
      toast.info('Demo mode not configured. Please register for an account.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center space-x-2">
            <Briefcase className="h-10 w-10 text-primary" />
            <span className="text-3xl font-bold">JobSeeker AI</span>
          </Link>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            Sign in to find your perfect job match
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Welcome Back</CardTitle>
            <CardDescription>
              Enter your credentials to access your account
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-9"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className="pl-9"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Remember Me & Forgot Password */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="remember"
                    checked={formData.remember}
                    onCheckedChange={(checked) => 
                      setFormData({ ...formData, remember: checked as boolean })
                    }
                    disabled={loading}
                  />
                  <Label htmlFor="remember" className="text-sm cursor-pointer">
                    Remember me
                  </Label>
                </div>
                
                <Link 
                  href="/forgot-password"
                  className="text-sm text-primary hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col space-y-2">
              <Button 
                type="submit" 
                className="w-full"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>

              <div className="relative w-full">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">
                    Or continue with
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleDemoLogin}
                  disabled={loading}
                >
                  Demo Account
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => router.push('/search')}
                  disabled={loading}
                >
                  Try Without Login
                </Button>
              </div>

              <p className="text-center text-sm text-gray-600 dark:text-gray-400">
                Don&apos;t have an account?{' '}
                <Link href="/register" className="text-primary hover:underline font-medium">
                  Sign up for free
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>

        {/* Security Notice */}
        <p className="text-center text-xs text-gray-500 mt-4">
          By signing in, you agree to our{' '}
          <Link href="/terms" className="hover:underline">Terms of Service</Link>
          {' '}and{' '}
          <Link href="/privacy" className="hover:underline">Privacy Policy</Link>
        </p>
      </div>
    </div>
  );
}