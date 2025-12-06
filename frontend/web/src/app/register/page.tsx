'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Briefcase, Mail, Lock, User, Loader2, AlertCircle, Check, X } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [passwordStrength, setPasswordStrength] = useState(0);
  const [passwordChecks, setPasswordChecks] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });

  const checkPasswordStrength = (password: string) => {
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    };

    setPasswordChecks(checks);

    const strength = Object.values(checks).filter(Boolean).length;
    setPasswordStrength((strength / 5) * 100);

    return checks;
  };

  const handlePasswordChange = (password: string) => {
    setFormData({ ...formData, password });
    checkPasswordStrength(password);
  };

  const validateForm = () => {
    if (!formData.full_name || !formData.email || !formData.password) {
      setError('Please fill in all fields');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }

    const strength = Object.values(passwordChecks).filter(Boolean).length;
    if (strength < 3) {
      setError('Password is too weak. Please use a stronger password.');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // Register user
      const registerResponse = await apiClient.register(
        formData.email,
        formData.password,
        formData.full_name
      );

      if (registerResponse.success) {
        // Auto-login after registration
        const loginResponse = await apiClient.login(formData.email, formData.password);
        
        if (loginResponse.access_token) {
          apiClient.setAuthToken(loginResponse.access_token);
          toast.success('Account created successfully!');
          
          // Redirect to profile setup
          router.push('/onboarding');
        }
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || 'Failed to create account. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrengthLabel = () => {
    if (passwordStrength === 0) return '';
    if (passwordStrength <= 20) return 'Very Weak';
    if (passwordStrength <= 40) return 'Weak';
    if (passwordStrength <= 60) return 'Fair';
    if (passwordStrength <= 80) return 'Good';
    return 'Strong';
  };

  const getPasswordStrengthColor = () => {
    if (passwordStrength <= 20) return 'bg-red-500';
    if (passwordStrength <= 40) return 'bg-orange-500';
    if (passwordStrength <= 60) return 'bg-yellow-500';
    if (passwordStrength <= 80) return 'bg-blue-500';
    return 'bg-green-500';
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
            Create your account to start finding jobs
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Get Started Free</CardTitle>
            <CardDescription>
              Join thousands finding their perfect job match with AI
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

              {/* Full Name */}
              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="full_name"
                    type="text"
                    placeholder="John Doe"
                    className="pl-9"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    required
                    disabled={loading}
                  />
                </div>
              </div>

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
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
                
                {formData.password && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Password strength:</span>
                      <span className={`font-medium ${passwordStrength > 60 ? 'text-green-600' : 'text-orange-600'}`}>
                        {getPasswordStrengthLabel()}
                      </span>
                    </div>
                    <Progress value={passwordStrength} className="h-2" />
                    
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="flex items-center space-x-1">
                        {passwordChecks.length ? 
                          <Check className="w-3 h-3 text-green-500" /> : 
                          <X className="w-3 h-3 text-gray-400" />
                        }
                        <span className={passwordChecks.length ? 'text-green-600' : 'text-gray-500'}>
                          8+ characters
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        {passwordChecks.uppercase ? 
                          <Check className="w-3 h-3 text-green-500" /> : 
                          <X className="w-3 h-3 text-gray-400" />
                        }
                        <span className={passwordChecks.uppercase ? 'text-green-600' : 'text-gray-500'}>
                          Uppercase letter
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        {passwordChecks.lowercase ? 
                          <Check className="w-3 h-3 text-green-500" /> : 
                          <X className="w-3 h-3 text-gray-400" />
                        }
                        <span className={passwordChecks.lowercase ? 'text-green-600' : 'text-gray-500'}>
                          Lowercase letter
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        {passwordChecks.number ? 
                          <Check className="w-3 h-3 text-green-500" /> : 
                          <X className="w-3 h-3 text-gray-400" />
                        }
                        <span className={passwordChecks.number ? 'text-green-600' : 'text-gray-500'}>
                          Number
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    className="pl-9"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    required
                    disabled={loading}
                  />
                </div>
                {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                  <p className="text-xs text-red-500">Passwords do not match</p>
                )}
              </div>
            </CardContent>

            <CardFooter className="flex flex-col space-y-2">
              <Button 
                type="submit" 
                className="w-full"
                disabled={loading || passwordStrength < 60}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  'Create Account'
                )}
              </Button>

              <div className="relative w-full">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">
                    Or
                  </span>
                </div>
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => router.push('/search')}
                disabled={loading}
              >
                Try Without Account
              </Button>

              <p className="text-center text-sm text-gray-600 dark:text-gray-400">
                Already have an account?{' '}
                <Link href="/login" className="text-primary hover:underline font-medium">
                  Sign in
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>

        {/* Terms Notice */}
        <p className="text-center text-xs text-gray-500 mt-4">
          By creating an account, you agree to our{' '}
          <Link href="/terms" className="hover:underline">Terms of Service</Link>
          {' '}and{' '}
          <Link href="/privacy" className="hover:underline">Privacy Policy</Link>
        </p>
      </div>
    </div>
  );
}