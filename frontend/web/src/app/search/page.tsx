'use client';

import { useState, useCallback } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import JobCard from '@/components/features/JobCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Search, 
  Filter, 
  Loader2, 
  AlertCircle,
  Briefcase,
  MapPin,
  DollarSign,
  X,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { Job, JobSearchForm, SearchResponse } from '@/lib/types';
import { toast } from 'sonner';

// Profession options based on backend support
const PROFESSIONS = [
  { value: 'software_engineer', label: 'Software Engineer' },
  { value: 'designer', label: 'Designer' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'sales', label: 'Sales' },
  { value: 'product_manager', label: 'Product Manager' },
  { value: 'data_scientist', label: 'Data Scientist' },
  { value: 'devops', label: 'DevOps' },
  { value: 'finance', label: 'Finance' },
  { value: 'hr', label: 'Human Resources' },
  { value: 'customer_support', label: 'Customer Support' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'education', label: 'Education' },
  { value: 'legal', label: 'Legal' },
  { value: 'operations', label: 'Operations' },
  { value: 'consulting', label: 'Consulting' },
];

export default function SearchPage() {
  const [searchForm, setSearchForm] = useState<JobSearchForm>({
    keywords: '',
    profession: '',
    location: '',
    remote_only: true,
    min_rate: undefined,
    max_rate: undefined,
  });

  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(true);
  const [salaryRange, setSalaryRange] = useState<number[]>([0, 200000]);

  const handleSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const formWithSalary = {
        ...searchForm,
        min_rate: salaryRange[0] > 0 ? salaryRange[0] : undefined,
        max_rate: salaryRange[1] < 200000 ? salaryRange[1] : undefined,
      };
      
      const response = await apiClient.searchJobs(formWithSalary);
      setSearchResults(response);
      
      if (response.success) {
        toast.success(`Found ${response.total_results} jobs across ${Object.keys(response.source_stats).length} job boards`);
      } else if (response.error) {
        setError(response.error);
        toast.error('Search failed: ' + response.error);
      }
    } catch (err) {
      const errorMessage = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail || (err as Error)?.message || 'Failed to search jobs';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [searchForm, salaryRange]);

  const handleSaveJob = (job: Job) => {
    const newSavedJobs = new Set(savedJobs);
    if (newSavedJobs.has(job.id)) {
      newSavedJobs.delete(job.id);
      toast.success('Job removed from saved');
    } else {
      newSavedJobs.add(job.id);
      toast.success('Job saved successfully');
    }
    setSavedJobs(newSavedJobs);
  };

  const handleApplyJob = async (job: Job) => {
    // In a real app, this would create an application
    window.open(job.url, '_blank');
    toast.success('Opening job application page...');
  };

  const handleViewJob = (job: Job) => {
    window.open(job.url, '_blank');
  };

  const clearFilters = () => {
    setSearchForm({
      keywords: '',
      profession: '',
      location: '',
      remote_only: true,
      min_rate: undefined,
      max_rate: undefined,
    });
    setSalaryRange([0, 200000]);
  };

  const formatSalary = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <AppLayout>
      <div className="flex gap-6">
        {/* Filters Sidebar */}
        <div className={`${showFilters ? 'w-80' : 'w-0'} transition-all duration-300 overflow-hidden`}>
          <Card className="sticky top-4">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="flex items-center gap-2">
                  <Filter className="w-5 h-5" />
                  Filters
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                >
                  Clear all
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Profession */}
              <div className="space-y-2">
                <Label htmlFor="profession">
                  <Briefcase className="w-4 h-4 inline mr-2" />
                  Profession
                </Label>
                <Select
                  value={searchForm.profession || 'all'}
                  onValueChange={(value) => setSearchForm({ ...searchForm, profession: value === 'all' ? '' : value })}
                >
                  <SelectTrigger id="profession">
                    <SelectValue placeholder="Select profession" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Professions</SelectItem>
                    {PROFESSIONS.map((prof) => (
                      <SelectItem key={prof.value} value={prof.value}>
                        {prof.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Location */}
              <div className="space-y-2">
                <Label htmlFor="location">
                  <MapPin className="w-4 h-4 inline mr-2" />
                  Location
                </Label>
                <Input
                  id="location"
                  placeholder="e.g., San Francisco, CA"
                  value={searchForm.location}
                  onChange={(e) => setSearchForm({ ...searchForm, location: e.target.value })}
                />
              </div>

              {/* Remote Only */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remote"
                  checked={searchForm.remote_only}
                  onCheckedChange={(checked) => 
                    setSearchForm({ ...searchForm, remote_only: checked as boolean })
                  }
                />
                <Label htmlFor="remote" className="cursor-pointer">
                  Remote positions only
                </Label>
              </div>

              {/* Salary Range */}
              <div className="space-y-2">
                <Label>
                  <DollarSign className="w-4 h-4 inline mr-2" />
                  Salary Range
                </Label>
                <div className="px-2">
                  <Slider
                    value={salaryRange}
                    onValueChange={setSalaryRange}
                    max={200000}
                    min={0}
                    step={5000}
                    className="mb-2"
                  />
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>{formatSalary(salaryRange[0])}</span>
                    <span>{formatSalary(salaryRange[1])}</span>
                  </div>
                </div>
              </div>

              {/* Job Boards */}
              {searchResults && searchResults.source_stats && (
                <div className="space-y-2">
                  <Label>Sources Found</Label>
                  <div className="space-y-1">
                    {Object.entries(searchResults.source_stats).map(([source, count]) => (
                      <div key={source} className="flex justify-between text-sm">
                        <span className="text-gray-600">{source}</span>
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          {/* Search Bar */}
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowFilters(!showFilters)}
                  className="lg:hidden"
                >
                  {showFilters ? <ChevronUp /> : <ChevronDown />}
                </Button>
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <Input
                    placeholder="Search by keywords, skills, or job title..."
                    className="pl-10 pr-4"
                    value={searchForm.keywords}
                    onChange={(e) => setSearchForm({ ...searchForm, keywords: e.target.value })}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                </div>
                <Button 
                  onClick={handleSearch}
                  disabled={loading}
                  className="min-w-[120px]"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4 mr-2" />
                      Search Jobs
                    </>
                  )}
                </Button>
              </div>

              {/* Active Filters */}
              {(searchForm.keywords || searchForm.profession || searchForm.location || 
                salaryRange[0] > 0 || salaryRange[1] < 200000) && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {searchForm.keywords && (
                    <Badge variant="secondary" className="flex items-center gap-1">
                      Keywords: {searchForm.keywords}
                      <X 
                        className="w-3 h-3 cursor-pointer" 
                        onClick={() => setSearchForm({ ...searchForm, keywords: '' })}
                      />
                    </Badge>
                  )}
                  {searchForm.profession && (
                    <Badge variant="secondary" className="flex items-center gap-1">
                      {PROFESSIONS.find(p => p.value === searchForm.profession)?.label}
                      <X 
                        className="w-3 h-3 cursor-pointer" 
                        onClick={() => setSearchForm({ ...searchForm, profession: '' })}
                      />
                    </Badge>
                  )}
                  {searchForm.location && (
                    <Badge variant="secondary" className="flex items-center gap-1">
                      {searchForm.location}
                      <X 
                        className="w-3 h-3 cursor-pointer" 
                        onClick={() => setSearchForm({ ...searchForm, location: '' })}
                      />
                    </Badge>
                  )}
                  {(salaryRange[0] > 0 || salaryRange[1] < 200000) && (
                    <Badge variant="secondary" className="flex items-center gap-1">
                      {formatSalary(salaryRange[0])} - {formatSalary(salaryRange[1])}
                      <X 
                        className="w-3 h-3 cursor-pointer" 
                        onClick={() => setSalaryRange([0, 200000])}
                      />
                    </Badge>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Results */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {searchResults && searchResults.success && (
            <div className="mb-4">
              <h2 className="text-lg font-semibold">
                Found {searchResults.total_results} jobs
              </h2>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
              <p className="text-lg font-medium">Searching across job boards...</p>
              <p className="text-sm text-gray-600 mt-2">This may take a few moments</p>
            </div>
          ) : searchResults && searchResults.jobs.length > 0 ? (
            <div className="space-y-4">
              {searchResults.jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onView={handleViewJob}
                  onSave={handleSaveJob}
                  onApply={handleApplyJob}
                  isSaved={savedJobs.has(job.id)}
                  showScore={false}
                />
              ))}
            </div>
          ) : searchResults ? (
            <Card className="py-12">
              <CardContent className="text-center">
                <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No jobs found</h3>
                <p className="text-gray-600">Try adjusting your filters or search terms</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="py-20">
              <CardContent className="text-center">
                <Briefcase className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-medium mb-2">Start your job search</h3>
                <p className="text-gray-600 mb-6">
                  Enter keywords or select filters to find your perfect job match
                </p>
                <Button onClick={handleSearch}>
                  <Search className="w-4 h-4 mr-2" />
                  Search Jobs
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </AppLayout>
  );
}