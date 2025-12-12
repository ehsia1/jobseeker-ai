'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  FileText,
  Upload,
  Loader2,
  Briefcase,
  Calendar,
  MapPin,
  CheckCircle,
  XCircle,
  Trash2,
  RefreshCw,
  Info,
  AlertCircle,
  GraduationCap,
  Award,
  Clock,
  Building,
  Mail,
  Phone,
  Globe,
  Github,
  Linkedin,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api/client';
import type { Resume, WorkExperience } from '@/lib/types';

interface ResumeUploadProps {
  onResumeLoaded?: (resume: Resume) => void;
}

export default function ResumeUpload({ onResumeLoaded }: ResumeUploadProps) {
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [resume, setResume] = useState<Resume | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pastedText, setPastedText] = useState('');
  const [activeTab, setActiveTab] = useState('upload');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ACCEPTED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

  const loadExistingResume = useCallback(async () => {
    try {
      console.log('[ResumeUpload] Loading existing resume...');
      const existingResume = await apiClient.getResume();
      console.log('[ResumeUpload] Got resume:', {
        id: existingResume?.id,
        full_name: existingResume?.full_name,
        parse_quality_score: existingResume?.parse_quality_score,
        total_experience_years: existingResume?.total_experience_years,
        work_experiences_count: existingResume?.work_experiences?.length,
        skills: existingResume?.skills?.slice(0, 5),
      });
      setResume(existingResume);
      onResumeLoaded?.(existingResume);
    } catch (err: any) {
      // No resume exists yet - that's fine
      if (err?.response?.status !== 404) {
        console.error('Failed to load resume:', err);
      } else {
        console.log('[ResumeUpload] No existing resume found (404)');
      }
    }
  }, [onResumeLoaded]);

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.endsWith('.txt')) {
      return 'Please upload a PDF, DOCX, or TXT file';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size must be less than 10MB';
    }
    return null;
  };

  const handleFileUpload = async (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      toast.error(validationError);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.uploadResume(file);
      setResume(response.resume);
      toast.success('Resume parsed successfully!');
      onResumeLoaded?.(response.resume);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || 'Failed to parse resume';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleTextParse = async () => {
    if (!pastedText.trim() || pastedText.trim().length < 50) {
      toast.error('Please paste your resume text (at least 50 characters)');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.parseResumeText(pastedText);
      setResume(response.resume);
      toast.success('Resume parsed successfully!');
      onResumeLoaded?.(response.resume);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || 'Failed to parse resume';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete your resume?')) return;

    setDeleting(true);
    try {
      await apiClient.deleteResume();
      setResume(null);
      setPastedText('');
      toast.success('Resume deleted');
    } catch (err: any) {
      toast.error('Failed to delete resume');
    } finally {
      setDeleting(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const getQualityColor = (score?: number) => {
    if (!score) return 'text-gray-500';
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Present';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  // Load existing resume on mount
  useEffect(() => {
    loadExistingResume();
  }, [loadExistingResume]);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-500" />
          Resume
        </CardTitle>
        <CardDescription>
          Upload your resume to auto-fill proposals with relevant experience
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4">
        {/* Error Display */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Resume Display (if loaded) */}
        {resume ? (
          <div className="flex-1 space-y-4 overflow-y-auto">
            {/* Header with actions */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-green-600 border-green-200">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Resume Loaded
                </Badge>
                {resume.parse_quality_score && (
                  <Badge variant="secondary" className={getQualityColor(resume.parse_quality_score)}>
                    {resume.parse_quality_score}% quality
                  </Badge>
                )}
              </div>
              <div className="flex gap-2">
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={loading}
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Replace resume</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDelete}
                        disabled={deleting}
                        className="text-red-500 hover:text-red-700"
                      >
                        {deleting ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Delete resume</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
            </div>

            {/* Contact Info */}
            <div className="bg-muted/50 rounded-lg p-4 space-y-2">
              {resume.full_name && (
                <h3 className="font-semibold text-lg">{resume.full_name}</h3>
              )}
              <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                {resume.email && (
                  <span className="flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5" />
                    {resume.email}
                  </span>
                )}
                {resume.phone && (
                  <span className="flex items-center gap-1">
                    <Phone className="w-3.5 h-3.5" />
                    {resume.phone}
                  </span>
                )}
                {resume.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" />
                    {resume.location}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                {resume.linkedin_url && (
                  <a href={resume.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center gap-1">
                    <Linkedin className="w-3.5 h-3.5" />
                    LinkedIn
                  </a>
                )}
                {resume.github_url && (
                  <a href={resume.github_url} target="_blank" rel="noopener noreferrer" className="text-gray-700 hover:underline flex items-center gap-1">
                    <Github className="w-3.5 h-3.5" />
                    GitHub
                  </a>
                )}
                {resume.portfolio_url && (
                  <a href={resume.portfolio_url} target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline flex items-center gap-1">
                    <Globe className="w-3.5 h-3.5" />
                    Portfolio
                  </a>
                )}
              </div>
            </div>

            {/* Summary */}
            {resume.summary && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-muted-foreground" />
                  Summary
                </Label>
                <p className="text-sm text-muted-foreground">{resume.summary}</p>
              </div>
            )}

            {/* Experience Overview */}
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span>{resume.total_experience_years} years experience</span>
              </div>
              <div className="flex items-center gap-2">
                <Building className="w-4 h-4 text-muted-foreground" />
                <span>{resume.work_experiences?.length || 0} positions</span>
              </div>
            </div>

            {/* Skills */}
            {resume.skills && resume.skills.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  Skills ({resume.skills.length})
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {resume.skills.slice(0, 15).map((skill) => (
                    <Badge key={skill} variant="secondary" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                  {resume.skills.length > 15 && (
                    <Badge variant="outline" className="text-xs">
                      +{resume.skills.length - 15} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {/* Work Experience */}
            {resume.work_experiences && resume.work_experiences.length > 0 && (
              <div className="space-y-3">
                <Label className="flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-blue-500" />
                  Work Experience
                </Label>
                <div className="space-y-3">
                  {resume.work_experiences.slice(0, 3).map((exp) => (
                    <div key={exp.id} className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium">{exp.title}</h4>
                          <p className="text-sm text-muted-foreground">{exp.company}</p>
                        </div>
                        <div className="text-right text-xs text-muted-foreground">
                          <p>{formatDate(exp.start_date)} - {exp.is_current ? 'Present' : formatDate(exp.end_date)}</p>
                          <p>{exp.duration_text}</p>
                        </div>
                      </div>
                      {exp.skills_used && exp.skills_used.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {exp.skills_used.slice(0, 5).map((skill) => (
                            <Badge key={skill} variant="outline" className="text-xs">
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {exp.achievements && exp.achievements.length > 0 && (
                        <ul className="text-xs text-muted-foreground space-y-1">
                          {exp.achievements.slice(0, 2).map((achievement, i) => (
                            <li key={i} className="flex items-start gap-1">
                              <span>•</span>
                              <span className="line-clamp-1">{achievement}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                  {resume.work_experiences.length > 3 && (
                    <p className="text-xs text-muted-foreground text-center">
                      +{resume.work_experiences.length - 3} more positions
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Education & Certifications */}
            <div className="grid grid-cols-2 gap-4">
              {resume.education && resume.education.length > 0 && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <GraduationCap className="w-4 h-4 text-purple-500" />
                    Education
                  </Label>
                  {resume.education.slice(0, 2).map((edu, i) => (
                    <div key={i} className="text-sm">
                      <p className="font-medium">{edu.degree}</p>
                      <p className="text-xs text-muted-foreground">{edu.school}</p>
                    </div>
                  ))}
                </div>
              )}
              {resume.certifications && resume.certifications.length > 0 && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Award className="w-4 h-4 text-yellow-500" />
                    Certifications
                  </Label>
                  <div className="flex flex-wrap gap-1">
                    {resume.certifications.slice(0, 3).map((cert) => (
                      <Badge key={cert} variant="outline" className="text-xs">
                        {cert}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* File info */}
            {resume.file_name && (
              <div className="text-xs text-muted-foreground border-t pt-3">
                Uploaded: {resume.file_name} • Parsed {resume.parsed_at ? new Date(resume.parsed_at).toLocaleDateString() : 'recently'}
              </div>
            )}
          </div>
        ) : (
          /* Upload Section */
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="upload">Upload File</TabsTrigger>
              <TabsTrigger value="paste">Paste Text</TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="flex-1 flex flex-col mt-4">
              <div
                className={`flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-8 transition-colors ${
                  dragActive
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.txt"
                  onChange={handleFileChange}
                />

                {loading ? (
                  <div className="text-center">
                    <Loader2 className="w-10 h-10 mx-auto mb-3 animate-spin text-blue-500" />
                    <p className="font-medium">Parsing resume...</p>
                    <p className="text-sm text-muted-foreground">This may take a moment</p>
                  </div>
                ) : (
                  <div className="text-center">
                    <Upload className="w-10 h-10 mx-auto mb-3 text-muted-foreground" />
                    <p className="font-medium mb-1">
                      Drag and drop your resume here
                    </p>
                    <p className="text-sm text-muted-foreground mb-4">
                      or click to browse
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Choose File
                    </Button>
                    <p className="text-xs text-muted-foreground mt-4">
                      Supports PDF, DOCX, TXT (max 10MB)
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="paste" className="flex-1 flex flex-col mt-4 space-y-4">
              <div className="flex-1 flex flex-col">
                <Label htmlFor="resume-text" className="mb-2">
                  Paste your resume content
                </Label>
                <Textarea
                  id="resume-text"
                  placeholder="Paste your resume text here...

Include your experience, skills, education, and achievements. The more detail you provide, the better we can match you with jobs and generate tailored proposals."
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                  className="flex-1 min-h-[200px] resize-none"
                />
                <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
                  <span>{pastedText.length} characters</span>
                  {pastedText.length > 0 && pastedText.length < 50 && (
                    <span className="text-yellow-600">Minimum 50 characters</span>
                  )}
                </div>
              </div>
              <Button
                onClick={handleTextParse}
                disabled={loading || pastedText.length < 50}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Parsing...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Parse Resume
                  </>
                )}
              </Button>
            </TabsContent>
          </Tabs>
        )}

        {/* Hidden file input for replace functionality */}
        {resume && (
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
          />
        )}
      </CardContent>
    </Card>
  );
}
