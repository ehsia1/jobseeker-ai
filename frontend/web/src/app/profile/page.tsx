'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import AppLayout from '@/components/layout/AppLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import {
  User,
  Briefcase,
  MapPin,
  DollarSign,
  Plus,
  X,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  FileText
} from 'lucide-react';
import ResumeUpload from '@/components/features/ResumeUpload';
import { useUserProfile } from '@/hooks/useAPI';
import { apiClient } from '@/lib/api/client';
import { UserProfileForm } from '@/lib/types';
import { toast } from 'sonner';

const PROFESSIONS = [
  { value: 'software_engineer', label: 'Software Engineer' },
  { value: 'data_scientist', label: 'Data Scientist' },
  { value: 'product_manager', label: 'Product Manager' },
  { value: 'designer', label: 'Designer' },
  { value: 'marketing', label: 'Marketing Professional' },
  { value: 'sales', label: 'Sales Professional' },
  { value: 'devops', label: 'DevOps Engineer' },
  { value: 'qa_engineer', label: 'QA Engineer' },
  { value: 'project_manager', label: 'Project Manager' },
  { value: 'business_analyst', label: 'Business Analyst' },
  { value: 'hr', label: 'Human Resources' },
  { value: 'finance', label: 'Finance Professional' },
  { value: 'consultant', label: 'Consultant' },
  { value: 'other', label: 'Other' },
];

const COMMON_SKILLS = [
  'JavaScript', 'TypeScript', 'React', 'Node.js', 'Python', 'Java', 
  'SQL', 'AWS', 'Docker', 'Kubernetes', 'Git', 'Agile', 'Scrum',
  'Machine Learning', 'Data Analysis', 'Project Management',
];

export default function ProfilePage() {
  const router = useRouter();
  const { profile, loading: profileLoading, refresh } = useUserProfile();
  const [loading, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState<UserProfileForm>({
    profession: '',
    job_title: '',
    skills: [],
    experience_years: 0,
    experience: '',
    education: '',
    certifications: [],
    preferences: {
      remote_only: true,
      industries: [],
      job_types: [],
      avoid_keywords: [],
    },
    min_rate_usd: undefined,
    location: '',
    portfolio: {},
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });

  const [newSkill, setNewSkill] = useState('');
  const [newCertification, setNewCertification] = useState('');
  const [newIndustry, setNewIndustry] = useState('');
  const [newAvoidKeyword, setNewAvoidKeyword] = useState('');

  useEffect(() => {
    if (profile) {
      setFormData({
        profession: profile.profession || '',
        job_title: profile.job_title || '',
        skills: profile.skills || [],
        experience_years: profile.experience_years || 0,
        experience: profile.experience || '',
        education: profile.education || '',
        certifications: profile.certifications || [],
        preferences: {
          remote_only: true,
          industries: [],
          job_types: [],
          avoid_keywords: [],
          ...profile.preferences,
        },
        min_rate_usd: profile.min_rate_usd,
        location: profile.location || '',
        portfolio: profile.portfolio || {},
        timezone: profile.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
    }
  }, [profile]);

  const handleSave = async () => {
    setError('');
    setSuccess(false);
    setSaving(true);

    try {
      const response = profile 
        ? await apiClient.updateUserProfile(formData)
        : await apiClient.createUserProfile(formData);

      if (response.success) {
        setSuccess(true);
        toast.success('Profile saved successfully!');
        refresh();
        
        // If this was first profile creation, redirect to dashboard
        if (!profile) {
          setTimeout(() => router.push('/dashboard'), 1500);
        }
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || 'Failed to save profile';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const addSkill = () => {
    if (newSkill && !formData.skills.includes(newSkill)) {
      setFormData({
        ...formData,
        skills: [...formData.skills, newSkill],
      });
      setNewSkill('');
    }
  };

  const removeSkill = (skill: string) => {
    setFormData({
      ...formData,
      skills: formData.skills.filter(s => s !== skill),
    });
  };

  const addCertification = () => {
    if (newCertification && !formData.certifications.includes(newCertification)) {
      setFormData({
        ...formData,
        certifications: [...formData.certifications, newCertification],
      });
      setNewCertification('');
    }
  };

  const removeCertification = (cert: string) => {
    setFormData({
      ...formData,
      certifications: formData.certifications.filter(c => c !== cert),
    });
  };

  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold">Profile Settings</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              Complete your profile to get better job matches
            </p>
          </div>

          {success && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                Profile saved successfully!
              </AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>
                Tell us about your professional background
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="profession">
                    <Briefcase className="w-4 h-4 inline mr-2" />
                    Profession
                  </Label>
                  <Select
                    value={formData.profession || 'all'}
                    onValueChange={(value) => 
                      setFormData({ ...formData, profession: value === 'all' ? '' : value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select profession" />
                    </SelectTrigger>
                    <SelectContent>
                      {PROFESSIONS.map((prof) => (
                        <SelectItem key={prof.value} value={prof.value}>
                          {prof.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="job_title">
                    <User className="w-4 h-4 inline mr-2" />
                    Current/Desired Job Title
                  </Label>
                  <Input
                    id="job_title"
                    placeholder="e.g., Senior Software Engineer"
                    value={formData.job_title}
                    onChange={(e) => setFormData({ ...formData, job_title: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="location">
                    <MapPin className="w-4 h-4 inline mr-2" />
                    Location
                  </Label>
                  <Input
                    id="location"
                    placeholder="e.g., San Francisco, CA"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="experience">
                    Years of Experience
                  </Label>
                  <div className="flex items-center space-x-4">
                    <Slider
                      value={[formData.experience_years || 0]}
                      onValueChange={([value]) => 
                        setFormData({ ...formData, experience_years: value })
                      }
                      max={30}
                      step={1}
                      className="flex-1"
                    />
                    <span className="w-12 text-right font-medium">
                      {formData.experience_years}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Skills */}
          <Card>
            <CardHeader>
              <CardTitle>Skills</CardTitle>
              <CardDescription>
                Add your technical and professional skills
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {formData.skills.map((skill) => (
                  <Badge key={skill} variant="secondary" className="px-3 py-1">
                    {skill}
                    <button
                      onClick={() => removeSkill(skill)}
                      className="ml-2 hover:text-destructive"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}
              </div>

              <div className="flex gap-2">
                <Input
                  placeholder="Add a skill..."
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill())}
                />
                <Button onClick={addSkill} size="icon">
                  <Plus className="w-4 h-4" />
                </Button>
              </div>

              <div className="flex flex-wrap gap-2">
                <p className="text-sm text-gray-600 w-full">Quick add:</p>
                {COMMON_SKILLS.filter(s => !formData.skills.includes(s)).map((skill) => (
                  <Button
                    key={skill}
                    variant="outline"
                    size="sm"
                    onClick={() => setFormData({
                      ...formData,
                      skills: [...formData.skills, skill],
                    })}
                  >
                    + {skill}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Resume */}
          <Card>
            <CardHeader>
              <CardTitle>
                <FileText className="w-5 h-5 inline mr-2" />
                Resume
              </CardTitle>
              <CardDescription>
                Upload your resume to auto-populate proposals with your experience
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResumeUpload />
            </CardContent>
          </Card>

          {/* Preferences */}
          <Card>
            <CardHeader>
              <CardTitle>Job Preferences</CardTitle>
              <CardDescription>
                Set your job search preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>
                  <DollarSign className="w-4 h-4 inline mr-2" />
                  Minimum Salary (USD/Year)
                </Label>
                <Input
                  type="number"
                  placeholder="e.g., 100000"
                  value={formData.min_rate_usd || ''}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    min_rate_usd: e.target.value ? parseInt(e.target.value) : undefined 
                  })}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remote"
                  checked={formData.preferences.remote_only}
                  onCheckedChange={(checked) => 
                    setFormData({
                      ...formData,
                      preferences: {
                        ...formData.preferences,
                        remote_only: checked as boolean,
                      },
                    })
                  }
                />
                <Label htmlFor="remote" className="cursor-pointer">
                  Remote positions only
                </Label>
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end space-x-4">
            <Button variant="outline" onClick={() => router.push('/dashboard')}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Profile
                </>
              )}
            </Button>
          </div>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}