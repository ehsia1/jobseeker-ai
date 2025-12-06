'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  FileText,
  Search,
  Loader2,
  Briefcase,
  MapPin,
  DollarSign,
  Clock,
  Building,
  CheckCircle,
  XCircle,
  Tag,
  Lightbulb,
  Info,
  AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api/client';
import type { ParsedJD, JDParseResponse, ScoreBreakdown } from '@/lib/types';

interface JDAnalyzerProps {
  onParsed?: (parsed: ParsedJD, score?: ScoreBreakdown) => void;
}

export default function JDAnalyzer({ onParsed }: JDAnalyzerProps) {
  const [jdText, setJDText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<JDParseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeJD = async () => {
    if (!jdText.trim()) {
      toast.error('Please paste a job description');
      return;
    }

    if (jdText.trim().length < 100) {
      toast.error('Job description seems too short. Please paste the full description.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.parseJobDescription(jdText);
      setResult(response);
      toast.success('Job description analyzed successfully!');
      onParsed?.(response.parsed, response.match_score);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || 'Failed to analyze job description';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-50 border-green-200';
    if (score >= 60) return 'bg-blue-50 border-blue-200';
    if (score >= 40) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
  };

  const formatCompensation = (min?: number, max?: number, type?: string) => {
    if (!min && !max) return null;
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    });
    const typeLabel = type === 'hourly' ? '/hr' : type === 'annual' ? '/yr' : '';
    if (min && max) return `${formatter.format(min)} - ${formatter.format(max)}${typeLabel}`;
    if (min) return `${formatter.format(min)}+${typeLabel}`;
    if (max) return `Up to ${formatter.format(max)}${typeLabel}`;
    return null;
  };

  const clearResults = () => {
    setResult(null);
    setJDText('');
    setError(null);
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-500" />
          Job Description Analyzer
        </CardTitle>
        <CardDescription>
          Paste a job description to extract key information and match with your profile
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col space-y-4">
        {/* Input Section */}
        <div className="space-y-2">
          <Label htmlFor="jd-text" className="flex items-center gap-2">
            Job Description
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="w-3.5 h-3.5 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">
                    Paste the full job description from any job board. Our AI will extract skills, requirements, and key details.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </Label>
          <Textarea
            id="jd-text"
            placeholder="Paste the job description here...

Example:
We are looking for a Senior Software Engineer with 5+ years of experience in Python and FastAPI. The ideal candidate should have experience with PostgreSQL, Redis, and AWS. Remote-friendly position with competitive salary..."
            value={jdText}
            onChange={(e) => setJDText(e.target.value)}
            className="min-h-[200px] resize-none"
          />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{jdText.length} characters</span>
            {jdText.length < 100 && jdText.length > 0 && (
              <span className="text-yellow-600">Minimum 100 characters recommended</span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            className="flex-1"
            onClick={analyzeJD}
            disabled={loading || !jdText.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="w-4 h-4 mr-2" />
                Analyze Job
              </>
            )}
          </Button>
          {result && (
            <Button variant="outline" onClick={clearResults}>
              Clear
            </Button>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Results Section */}
        {result && (
          <div className="flex-1 space-y-4 overflow-y-auto">
            {/* Match Score */}
            {result.match_score && (
              <div className={`rounded-lg border p-4 ${getScoreBg(result.match_score.total)}`}>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold">Profile Match Score</h4>
                  <span className={`text-2xl font-bold ${getScoreColor(result.match_score.total)}`}>
                    {Math.round(result.match_score.total)}%
                  </span>
                </div>
                <Progress value={result.match_score.total} className="h-2 mb-3" />
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {result.match_score.skill_match !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Skills</span>
                      <span className="font-medium">{Math.round(result.match_score.skill_match)}%</span>
                    </div>
                  )}
                  {result.match_score.experience_match !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Experience</span>
                      <span className="font-medium">{Math.round(result.match_score.experience_match)}%</span>
                    </div>
                  )}
                  {result.match_score.compensation_match !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Compensation</span>
                      <span className="font-medium">{Math.round(result.match_score.compensation_match)}%</span>
                    </div>
                  )}
                  {result.match_score.location_match !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Location</span>
                      <span className="font-medium">{Math.round(result.match_score.location_match)}%</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Job Overview */}
            <div className="space-y-3">
              {result.parsed.title && (
                <div className="flex items-start gap-2">
                  <Briefcase className="w-4 h-4 mt-1 text-muted-foreground" />
                  <div>
                    <span className="text-xs text-muted-foreground">Title</span>
                    <p className="font-medium">{result.parsed.title}</p>
                  </div>
                </div>
              )}

              {result.parsed.company && (
                <div className="flex items-start gap-2">
                  <Building className="w-4 h-4 mt-1 text-muted-foreground" />
                  <div>
                    <span className="text-xs text-muted-foreground">Company</span>
                    <p className="font-medium">{result.parsed.company}</p>
                  </div>
                </div>
              )}

              {(result.parsed.location || result.parsed.remote) && (
                <div className="flex items-start gap-2">
                  <MapPin className="w-4 h-4 mt-1 text-muted-foreground" />
                  <div>
                    <span className="text-xs text-muted-foreground">Location</span>
                    <p className="font-medium">
                      {result.parsed.location || 'Not specified'}
                      {result.parsed.remote && (
                        <Badge variant="secondary" className="ml-2 text-xs">Remote OK</Badge>
                      )}
                    </p>
                  </div>
                </div>
              )}

              {formatCompensation(
                result.parsed.compensation_min,
                result.parsed.compensation_max,
                result.parsed.compensation_type
              ) && (
                <div className="flex items-start gap-2">
                  <DollarSign className="w-4 h-4 mt-1 text-muted-foreground" />
                  <div>
                    <span className="text-xs text-muted-foreground">Compensation</span>
                    <p className="font-medium">
                      {formatCompensation(
                        result.parsed.compensation_min,
                        result.parsed.compensation_max,
                        result.parsed.compensation_type
                      )}
                    </p>
                  </div>
                </div>
              )}

              {result.parsed.experience_level && (
                <div className="flex items-start gap-2">
                  <Clock className="w-4 h-4 mt-1 text-muted-foreground" />
                  <div>
                    <span className="text-xs text-muted-foreground">Experience Level</span>
                    <p className="font-medium">
                      {result.parsed.experience_level}
                      {result.parsed.experience_years_min && (
                        <span className="text-muted-foreground ml-2">
                          ({result.parsed.experience_years_min}
                          {result.parsed.experience_years_max
                            ? `-${result.parsed.experience_years_max}`
                            : '+'} years)
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Required Skills */}
            {result.parsed.required_skills.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  Required Skills
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {result.parsed.required_skills.map((skill) => (
                    <Badge key={skill} variant="default" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Nice-to-Have Skills */}
            {result.parsed.nice_to_have_skills.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-yellow-500" />
                  Nice to Have
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {result.parsed.nice_to_have_skills.map((skill) => (
                    <Badge key={skill} variant="outline" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Keywords to Emphasize */}
            {result.parsed.keywords_to_emphasize.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-purple-500" />
                  Keywords to Emphasize
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {result.parsed.keywords_to_emphasize.map((keyword) => (
                    <Badge key={keyword} variant="secondary" className="text-xs bg-purple-50 text-purple-700">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Key Requirements */}
            {result.parsed.key_requirements.length > 0 && (
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-blue-500" />
                  Key Requirements
                </Label>
                <ul className="space-y-1 text-sm">
                  {result.parsed.key_requirements.slice(0, 5).map((req, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-muted-foreground">•</span>
                      <span>{req}</span>
                    </li>
                  ))}
                  {result.parsed.key_requirements.length > 5 && (
                    <li className="text-muted-foreground text-xs">
                      +{result.parsed.key_requirements.length - 5} more
                    </li>
                  )}
                </ul>
              </div>
            )}

            {/* Explanation */}
            {result.explanation && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  {result.explanation}
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Empty State */}
        {!result && !loading && (
          <div className="flex-1 flex items-center justify-center border-2 border-dashed rounded-lg">
            <div className="text-center text-muted-foreground p-8">
              <FileText className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p className="text-sm">
                Paste a job description above to analyze it
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
