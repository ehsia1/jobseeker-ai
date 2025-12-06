'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  Target, 
  Briefcase, 
  DollarSign, 
  MapPin, 
  Clock, 
  Heart,
  TrendingUp,
  Info
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ScoreBreakdownProps {
  totalScore: number;
  breakdown: {
    semantic_similarity?: number;
    skill_match?: number;
    experience_match?: number;
    compensation_match?: number;
    location_match?: number;
    freshness_score?: number;
    preference_match?: number;
  };
  explanation?: string;
  compact?: boolean;
}

export default function ScoreBreakdown({ 
  totalScore, 
  breakdown, 
  explanation,
  compact = false 
}: ScoreBreakdownProps) {
  
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 60) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-blue-500';
    if (score >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 90) return 'Excellent Match';
    if (score >= 80) return 'Great Match';
    if (score >= 70) return 'Good Match';
    if (score >= 60) return 'Fair Match';
    if (score >= 50) return 'Possible Match';
    return 'Low Match';
  };

  const scoreFactors = [
    {
      key: 'skill_match',
      label: 'Skills',
      icon: Briefcase,
      weight: 25,
      description: 'How well your skills match the job requirements'
    },
    {
      key: 'semantic_similarity',
      label: 'Relevance',
      icon: Target,
      weight: 25,
      description: 'Overall similarity to your profile and experience'
    },
    {
      key: 'experience_match',
      label: 'Experience',
      icon: TrendingUp,
      weight: 20,
      description: 'How your experience level matches requirements'
    },
    {
      key: 'compensation_match',
      label: 'Compensation',
      icon: DollarSign,
      weight: 15,
      description: 'Salary alignment with your expectations'
    },
    {
      key: 'location_match',
      label: 'Location',
      icon: MapPin,
      weight: 10,
      description: 'Location compatibility and remote options'
    },
    {
      key: 'freshness_score',
      label: 'Freshness',
      icon: Clock,
      weight: 5,
      description: 'How recently the job was posted'
    },
    {
      key: 'preference_match',
      label: 'Preferences',
      icon: Heart,
      weight: 5,
      description: 'Match with your job preferences'
    },
  ];

  if (compact) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`px-3 py-1 rounded-lg border ${getScoreColor(totalScore)}`}>
              <span className="text-2xl font-bold">{Math.round(totalScore)}%</span>
            </div>
            <Badge variant="outline" className="font-medium">
              {getScoreLabel(totalScore)}
            </Badge>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-2">
          {scoreFactors.slice(0, 4).map((factor) => {
            const score = breakdown[factor.key as keyof typeof breakdown] || 0;
            return (
              <div key={factor.key} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-1">
                  <factor.icon className="w-3 h-3" />
                  {factor.label}
                </span>
                <span className="font-medium">{Math.round(score)}%</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            Match Score Analysis
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="w-4 h-4 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">
                    AI-powered scoring based on 7 factors to find your perfect job match
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </CardTitle>
          <div className={`px-4 py-2 rounded-lg border ${getScoreColor(totalScore)}`}>
            <div className="text-center">
              <div className="text-3xl font-bold">{Math.round(totalScore)}%</div>
              <div className="text-xs">{getScoreLabel(totalScore)}</div>
            </div>
          </div>
        </div>
        {explanation && (
          <CardDescription className="mt-3">
            {explanation}
          </CardDescription>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Overall Match</span>
            <span className="text-muted-foreground">{Math.round(totalScore)}%</span>
          </div>
          <Progress 
            value={totalScore} 
            className="h-3"
            indicatorClassName={getProgressColor(totalScore)}
          />
        </div>

        {/* Factor Breakdown */}
        <div className="space-y-3 pt-2">
          {scoreFactors.map((factor) => {
            const score = breakdown[factor.key as keyof typeof breakdown] || 0;
            const Icon = factor.icon;
            
            return (
              <div key={factor.key} className="space-y-1">
                <div className="flex items-center justify-between">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-center gap-2 cursor-help">
                          <Icon className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm font-medium">{factor.label}</span>
                          <Badge variant="outline" className="text-xs px-1.5 py-0">
                            {factor.weight}%
                          </Badge>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs text-xs">{factor.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  <span className="text-sm font-medium">{Math.round(score)}%</span>
                </div>
                <Progress 
                  value={score} 
                  className="h-2"
                  indicatorClassName={getProgressColor(score)}
                />
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="pt-4 border-t">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Score Range:</span>
            <div className="flex gap-3">
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                80-100 Excellent
              </span>
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-blue-500" />
                60-79 Good
              </span>
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-yellow-500" />
                40-59 Fair
              </span>
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                0-39 Low
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}