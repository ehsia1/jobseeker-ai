import React, { useCallback, useState, useMemo } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  AccessibilityInfo,
} from 'react-native';
import { Text, Searchbar, Chip, ProgressBar, Button, Portal, Modal, IconButton, TextInput } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useJobsInfinite, useMatchesInfinite, useSaveJob } from '../../src/hooks/useJobs';
import { useJobRadar } from '../../src/hooks/useAgent';
import JobCard from '../../src/components/JobCard';
import type { Job, ScoredJob, JobRadarMatch, JobFilters } from '@jobseeker/shared';

// Score color coding helper
const getScoreColor = (score: number): { bg: string; text: string; label: string } => {
  if (score >= 85) return { bg: '#dcfce7', text: '#166534', label: 'Excellent match' };
  if (score >= 70) return { bg: '#dbeafe', text: '#1d4ed8', label: 'Good match' };
  if (score >= 55) return { bg: '#fef3c7', text: '#92400e', label: 'Fair match' };
  return { bg: '#fee2e2', text: '#dc2626', label: 'Low match' };
};

// Radar step mapping for progress display
const RADAR_STEPS = [
  { pattern: /starting|initializing/i, step: 1, total: 5 },
  { pattern: /fetching|loading jobs/i, step: 2, total: 5 },
  { pattern: /analyzing|scoring/i, step: 3, total: 5 },
  { pattern: /ranking|sorting/i, step: 4, total: 5 },
  { pattern: /finalizing|complet/i, step: 5, total: 5 },
];

const getStepInfo = (currentStep: string): { step: number; total: number } | null => {
  for (const { pattern, step, total } of RADAR_STEPS) {
    if (pattern.test(currentStep)) {
      return { step, total };
    }
  }
  return null;
};

export default function JobFeedScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [radarModalVisible, setRadarModalVisible] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [selectedRateRange, setSelectedRateRange] = useState<string | null>(null);
  const [location, setLocation] = useState('');
  const [source, setSource] = useState<string | undefined>(undefined);

  // Preset rate range options
  const rateRanges = [
    { label: '$25-50/hr', value: '25-50', min: 25, max: 50 },
    { label: '$50-100/hr', value: '50-100', min: 50, max: 100 },
    { label: '$100-150/hr', value: '100-150', min: 100, max: 150 },
    { label: '$150+/hr', value: '150+', min: 150, max: undefined },
  ];

  // Get min/max from selected range
  const selectedRange = rateRanges.find(r => r.value === selectedRateRange);

  // Build filters object
  const filters: JobFilters = useMemo(() => ({
    remote_only: remoteOnly || undefined,
    min_rate: selectedRange?.min,
    max_rate: selectedRange?.max,
    location: location || undefined,
    source: source || undefined,
  }), [remoteOnly, selectedRange, location, source]);

  // Check if any filters are active
  const hasActiveFilters = remoteOnly || selectedRateRange || location || source;

  // Job Radar agent
  const jobRadar = useJobRadar();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useJobsInfinite({ filters });

  // Fetch matches to know which jobs are saved
  const { data: matchesData } = useMatchesInfinite();

  // Save job mutation
  const saveJobMutation = useSaveJob();

  const jobs = data?.pages.flatMap((page) => page.jobs) ?? [];

  // Create a Set of saved job IDs for quick lookup
  const savedJobIds = useMemo(() => {
    const allMatches = matchesData?.pages.flatMap((page) => page.items) ?? [];
    return new Set(allMatches.map((match) => match.job_id));
  }, [matchesData]);

  const handleJobPress = useCallback(
    (job: Job | ScoredJob) => {
      router.push(`/job/${job.id}`);
    },
    [router]
  );

  const handleSave = useCallback((job: Job | ScoredJob) => {
    // Don't save if already saved
    if (savedJobIds.has(job.id)) {
      Alert.alert('Already Saved', 'This job is already in your saved matches.');
      return;
    }

    saveJobMutation.mutate(job.id, {
      onSuccess: () => {
        Alert.alert('Saved!', 'Job has been added to your matches.');
      },
      onError: (err) => {
        Alert.alert('Error', err.message || 'Failed to save job. Please try again.');
      },
    });
  }, [savedJobIds, saveJobMutation]);

  const handleApply = useCallback((job: Job | ScoredJob) => {
    // Navigate to job details with apply intent
    router.push(`/job/${job.id}?action=apply`);
  }, [router]);

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Run Job Radar with current filters
  const handleRunRadar = useCallback(() => {
    const keywords = searchQuery.trim() ? searchQuery.trim().split(/\s+/) : undefined;
    jobRadar.run({
      keywords,
      remote_only: remoteOnly,
      min_score: 60,
      generate_proposals: false,
    });
  }, [searchQuery, remoteOnly, jobRadar]);

  // Navigate to a job from radar results
  const handleRadarJobPress = useCallback((match: JobRadarMatch) => {
    setRadarModalVisible(false);
    router.push(`/job/${match.job_id}`);
  }, [router]);

  const renderItem = useCallback(
    ({ item }: { item: Job | ScoredJob }) => (
      <JobCard
        job={item}
        onPress={handleJobPress}
        onSave={handleSave}
        onApply={handleApply}
        isSaved={savedJobIds.has(item.id)}
      />
    ),
    [handleJobPress, handleSave, handleApply, savedJobIds]
  );

  const renderFooter = useCallback(() => {
    if (!isFetchingNextPage) return null;
    return (
      <View style={styles.loadingFooter}>
        <ActivityIndicator size="small" color="#3b82f6" />
      </View>
    );
  }, [isFetchingNextPage]);

  const renderEmpty = useCallback(() => {
    if (isLoading) return null;
    return (
      <View style={styles.emptyContainer}>
        <Text variant="headlineSmall" style={styles.emptyTitle}>
          No jobs found
        </Text>
        <Text variant="bodyMedium" style={styles.emptyText}>
          {remoteOnly
            ? 'Try turning off the remote filter'
            : 'Pull down to refresh or check back later'}
        </Text>
      </View>
    );
  }, [isLoading, remoteOnly]);

  if (isError) {
    return (
      <View style={styles.errorContainer}>
        <Text variant="headlineSmall" style={styles.errorTitle}>
          Something went wrong
        </Text>
        <Text variant="bodyMedium" style={styles.errorText}>
          {error?.message || 'Failed to load jobs'}
        </Text>
        <Text
          variant="bodyMedium"
          style={styles.retryLink}
          onPress={() => refetch()}
        >
          Tap to retry
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Searchbar
          placeholder="Search jobs..."
          onChangeText={setSearchQuery}
          value={searchQuery}
          style={styles.searchbar}
          inputStyle={styles.searchInput}
        />
        <View style={styles.filters} accessibilityRole="toolbar" accessibilityLabel="Job filters">
          <Chip
            selected={remoteOnly}
            onPress={() => setRemoteOnly(!remoteOnly)}
            style={styles.chip}
            textStyle={styles.chipText}
            showSelectedOverlay
            accessibilityRole="checkbox"
            accessibilityState={{ checked: remoteOnly }}
            accessibilityLabel="Filter by remote only jobs"
          >
            Remote Only
          </Chip>
          <Chip
            icon={showFilters ? 'chevron-up' : 'filter-variant'}
            onPress={() => setShowFilters(!showFilters)}
            style={[styles.chip, hasActiveFilters && styles.activeFilterChip]}
            textStyle={styles.chipText}
            accessibilityRole="button"
            accessibilityState={{ expanded: showFilters }}
            accessibilityLabel={`Advanced filters${hasActiveFilters ? ', active' : ''}`}
            accessibilityHint="Tap to expand filter options"
          >
            Filters{hasActiveFilters ? ' •' : ''}
          </Chip>
          <Button
            mode="contained"
            onPress={handleRunRadar}
            disabled={jobRadar.isRunning}
            style={styles.radarButton}
            labelStyle={styles.radarButtonLabel}
            icon="radar"
            compact
            accessibilityRole="button"
            accessibilityLabel={jobRadar.isRunning ? 'Job Radar scanning in progress' : 'Run Job Radar to find matching jobs'}
            accessibilityHint="AI-powered job matching based on your profile"
          >
            {jobRadar.isRunning ? 'Scanning...' : 'Job Radar'}
          </Button>
        </View>

        {/* Expandable Filter Panel */}
        {showFilters && (
          <View style={styles.filterPanel}>
            {/* Rate Range Chips */}
            <View style={styles.filterSection}>
              <Text variant="labelMedium" style={styles.filterLabel}>Hourly Rate:</Text>
              <View style={styles.rateChips}>
                {rateRanges.map((range) => (
                  <Chip
                    key={range.value}
                    selected={selectedRateRange === range.value}
                    onPress={() => setSelectedRateRange(
                      selectedRateRange === range.value ? null : range.value
                    )}
                    style={[
                      styles.rateChip,
                      selectedRateRange === range.value && styles.rateChipSelected
                    ]}
                    textStyle={[
                      styles.rateChipText,
                      selectedRateRange === range.value && styles.rateChipTextSelected
                    ]}
                    showSelectedOverlay
                  >
                    {range.label}
                  </Chip>
                ))}
              </View>
            </View>

            {/* Location Input */}
            <TextInput
              label="Location"
              value={location}
              onChangeText={setLocation}
              style={styles.filterInputFull}
              mode="outlined"
              dense
              placeholder="e.g. San Francisco, New York"
            />

            {/* Source Chips */}
            <View style={styles.filterSection}>
              <Text variant="labelMedium" style={styles.filterLabel}>Source:</Text>
              <View style={styles.sourceFilters}>
                {['upwork', 'linkedin', 'indeed'].map((s) => (
                  <Chip
                    key={s}
                    selected={source === s}
                    onPress={() => setSource(source === s ? undefined : s)}
                    style={styles.sourceChip}
                    textStyle={styles.sourceChipText}
                    compact
                  >
                    {s}
                  </Chip>
                ))}
              </View>
            </View>

            {hasActiveFilters && (
              <Button
                mode="text"
                onPress={() => {
                  setRemoteOnly(false);
                  setSelectedRateRange(null);
                  setLocation('');
                  setSource(undefined);
                }}
                compact
                style={styles.clearButton}
              >
                Clear All Filters
              </Button>
            )}
          </View>
        )}

        {/* Job Radar Progress Banner */}
        {jobRadar.isRunning && (
          <View
            style={styles.radarBanner}
            accessible={true}
            accessibilityRole="progressbar"
            accessibilityLabel={`Job Radar scanning: ${jobRadar.progress}% complete`}
            accessibilityValue={{ now: jobRadar.progress, min: 0, max: 100 }}
          >
            <View style={styles.radarBannerContent}>
              <ActivityIndicator size="small" color="#3b82f6" />
              <View style={styles.radarBannerText}>
                {(() => {
                  const stepInfo = getStepInfo(jobRadar.currentStep);
                  return (
                    <>
                      {stepInfo && (
                        <Text variant="labelSmall" style={styles.radarStepNumber}>
                          Step {stepInfo.step} of {stepInfo.total}
                        </Text>
                      )}
                      <Text variant="bodySmall" style={styles.radarStep}>
                        {jobRadar.currentStep || 'Starting radar scan...'}
                      </Text>
                    </>
                  );
                })()}
              </View>
            </View>
            <ProgressBar
              progress={jobRadar.progress / 100}
              color="#3b82f6"
              style={styles.radarProgress}
            />
          </View>
        )}

        {/* Job Radar Completed Banner */}
        {jobRadar.isCompleted && jobRadar.result && (
          <TouchableOpacity
            style={styles.radarCompleteBanner}
            onPress={() => setRadarModalVisible(true)}
            accessible={true}
            accessibilityRole="button"
            accessibilityLabel={`Job Radar found ${jobRadar.result.matches_found} matches. Tap to view results.`}
            accessibilityHint="Opens the results modal with all matches"
          >
            <View style={styles.radarCompleteContent}>
              <View style={styles.radarCompleteMain}>
                <Text variant="bodyMedium" style={styles.radarCompleteText}>
                  Found {jobRadar.result.matches_found} matches!
                </Text>
                {/* Top match preview */}
                {jobRadar.result.top_matches.length > 0 && (
                  <View style={styles.topMatchPreview}>
                    <Text variant="bodySmall" style={styles.topMatchLabel}>
                      Top match:
                    </Text>
                    <Text variant="bodySmall" style={styles.topMatchTitle} numberOfLines={1}>
                      {jobRadar.result.top_matches[0].title}
                    </Text>
                    <View style={[
                      styles.topMatchScore,
                      { backgroundColor: getScoreColor(jobRadar.result.top_matches[0].score).bg }
                    ]}>
                      <Text style={[
                        styles.topMatchScoreText,
                        { color: getScoreColor(jobRadar.result.top_matches[0].score).text }
                      ]}>
                        {jobRadar.result.top_matches[0].score}%
                      </Text>
                    </View>
                  </View>
                )}
              </View>
              <View style={styles.radarCompleteActions}>
                <Button
                  mode="text"
                  onPress={() => setRadarModalVisible(true)}
                  compact
                  labelStyle={styles.viewAllLabel}
                >
                  View All
                </Button>
                <Button
                  mode="text"
                  onPress={() => jobRadar.reset()}
                  compact
                  labelStyle={styles.dismissLabel}
                >
                  Dismiss
                </Button>
              </View>
            </View>
          </TouchableOpacity>
        )}

        {/* Job Radar Error Banner */}
        {jobRadar.isFailed && (
          <View
            style={styles.radarErrorBanner}
            accessible={true}
            accessibilityRole="alert"
            accessibilityLabel={`Job Radar scan failed: ${jobRadar.errors[0] || 'Unknown error'}`}
          >
            <View style={styles.radarErrorContent}>
              <Text variant="bodySmall" style={styles.radarErrorText}>
                Radar scan failed: {jobRadar.errors[0] || 'Unknown error'}
              </Text>
              <Text variant="bodySmall" style={styles.radarErrorHint}>
                This might be a temporary issue. Try again or adjust your filters.
              </Text>
            </View>
            <View style={styles.radarErrorActions}>
              <Button
                mode="contained"
                onPress={handleRunRadar}
                compact
                style={styles.retryButton}
                labelStyle={styles.retryButtonLabel}
                icon="refresh"
              >
                Retry
              </Button>
              <Button
                mode="text"
                onPress={() => jobRadar.reset()}
                compact
                labelStyle={styles.dismissLabel}
              >
                Dismiss
              </Button>
            </View>
          </View>
        )}
      </View>

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3b82f6" />
          <Text variant="bodyMedium" style={styles.loadingText}>
            Finding your best matches...
          </Text>
        </View>
      ) : (
        <FlatList
          data={jobs}
          renderItem={renderItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          onEndReached={loadMore}
          onEndReachedThreshold={0.5}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={refetch}
              tintColor="#3b82f6"
              colors={['#3b82f6']}
            />
          }
          ListFooterComponent={renderFooter}
          ListEmptyComponent={renderEmpty}
          showsVerticalScrollIndicator={false}
          initialNumToRender={10}
          maxToRenderPerBatch={10}
          windowSize={5}
        />
      )}

      {/* Job Radar Results Modal */}
      <Portal>
        <Modal
          visible={radarModalVisible}
          onDismiss={() => setRadarModalVisible(false)}
          contentContainerStyle={styles.modalContent}
        >
          <View style={styles.modalHeader}>
            <Text variant="titleLarge" style={styles.modalTitle}>
              Job Radar Results
            </Text>
            <TouchableOpacity
              onPress={() => setRadarModalVisible(false)}
              accessible={true}
              accessibilityRole="button"
              accessibilityLabel="Close results modal"
            >
              <Text style={styles.modalClose}>✕</Text>
            </TouchableOpacity>
          </View>

          {jobRadar.result && (
            <>
              <View style={styles.modalStats}>
                <View style={styles.statItem} accessible={true} accessibilityLabel={`${jobRadar.result.jobs_found} jobs scanned`}>
                  <Text variant="headlineMedium" style={styles.statNumber}>
                    {jobRadar.result.jobs_found}
                  </Text>
                  <Text variant="bodySmall" style={styles.statLabel}>
                    Jobs Scanned
                  </Text>
                </View>
                <View style={styles.statItem} accessible={true} accessibilityLabel={`${jobRadar.result.matches_found} matches found`}>
                  <Text variant="headlineMedium" style={styles.statNumber}>
                    {jobRadar.result.matches_found}
                  </Text>
                  <Text variant="bodySmall" style={styles.statLabel}>
                    Matches
                  </Text>
                </View>
              </View>

              {/* Score Legend */}
              <View style={styles.scoreLegend}>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#166534' }]} />
                  <Text variant="labelSmall" style={styles.legendText}>85%+ Excellent</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#1d4ed8' }]} />
                  <Text variant="labelSmall" style={styles.legendText}>70%+ Good</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#92400e' }]} />
                  <Text variant="labelSmall" style={styles.legendText}>55%+ Fair</Text>
                </View>
              </View>

              <FlatList
                data={jobRadar.result.top_matches}
                keyExtractor={(item) => item.job_id}
                style={styles.matchesList}
                renderItem={({ item }) => {
                  const scoreColors = getScoreColor(item.score);
                  const isAlreadySaved = savedJobIds.has(item.job_id);
                  return (
                    <View
                      style={styles.matchItem}
                      accessible={true}
                      accessibilityLabel={`${item.title} at ${item.company}, ${item.score}% match. ${scoreColors.label}`}
                    >
                      <TouchableOpacity
                        onPress={() => handleRadarJobPress(item)}
                        style={styles.matchContent}
                      >
                        <View style={styles.matchHeader}>
                          <Text variant="bodyLarge" style={styles.matchTitle} numberOfLines={1}>
                            {item.title}
                          </Text>
                          <View style={[styles.matchScore, { backgroundColor: scoreColors.bg }]}>
                            <Text variant="labelMedium" style={[styles.scoreText, { color: scoreColors.text }]}>
                              {item.score}%
                            </Text>
                          </View>
                        </View>
                        <Text variant="bodySmall" style={styles.matchCompany} numberOfLines={1}>
                          {item.company} {item.location && `• ${item.location}`}
                          {item.remote && ' • Remote'}
                        </Text>
                        {item.explanation && (
                          <Text variant="bodySmall" style={styles.matchExplanation} numberOfLines={3}>
                            {item.explanation}
                          </Text>
                        )}
                      </TouchableOpacity>
                      {/* Action buttons */}
                      <View style={styles.matchActions}>
                        <Button
                          mode="outlined"
                          onPress={() => {
                            if (!isAlreadySaved) {
                              saveJobMutation.mutate(item.job_id, {
                                onSuccess: () => Alert.alert('Saved!', 'Job added to your matches.'),
                                onError: (err) => Alert.alert('Error', err.message),
                              });
                            }
                          }}
                          compact
                          style={[styles.matchActionButton, isAlreadySaved && styles.matchActionButtonDisabled]}
                          labelStyle={styles.matchActionLabel}
                          icon={isAlreadySaved ? 'check' : 'bookmark-outline'}
                          disabled={isAlreadySaved}
                        >
                          {isAlreadySaved ? 'Saved' : 'Save'}
                        </Button>
                        <Button
                          mode="contained"
                          onPress={() => {
                            setRadarModalVisible(false);
                            router.push(`/job/${item.job_id}?action=apply`);
                          }}
                          compact
                          style={styles.matchActionButton}
                          labelStyle={styles.matchActionLabel}
                          icon="send"
                        >
                          Apply
                        </Button>
                      </View>
                    </View>
                  );
                }}
                ListEmptyComponent={
                  <Text style={styles.noMatches}>No high-scoring matches found</Text>
                }
              />
            </>
          )}
        </Modal>
      </Portal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  header: {
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  searchbar: {
    elevation: 0,
    backgroundColor: '#f3f4f6',
    borderRadius: 8,
  },
  searchInput: {
    fontSize: 14,
  },
  filters: {
    flexDirection: 'row',
    marginTop: 8,
  },
  chip: {
    backgroundColor: '#e0e7ff',
  },
  chipText: {
    fontSize: 12,
  },
  activeFilterChip: {
    backgroundColor: '#c7d2fe',
    borderColor: '#6366f1',
    borderWidth: 1,
  },
  // Filter Panel styles
  filterPanel: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  filterSection: {
    marginBottom: 12,
  },
  filterLabel: {
    color: '#6b7280',
    marginBottom: 8,
  },
  rateChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  rateChip: {
    backgroundColor: '#f3f4f6',
  },
  rateChipSelected: {
    backgroundColor: '#dbeafe',
  },
  rateChipText: {
    fontSize: 12,
  },
  rateChipTextSelected: {
    color: '#1d4ed8',
    fontWeight: '500',
  },
  filterInputFull: {
    backgroundColor: '#fff',
    marginBottom: 12,
  },
  sourceFilters: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  sourceChip: {
    backgroundColor: '#f3f4f6',
  },
  sourceChipText: {
    fontSize: 11,
    textTransform: 'capitalize',
  },
  clearButton: {
    marginTop: 4,
    alignSelf: 'flex-start',
  },
  listContent: {
    padding: 16,
    paddingBottom: 32,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#6b7280',
  },
  loadingFooter: {
    paddingVertical: 16,
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
    paddingTop: 64,
  },
  emptyTitle: {
    color: '#374151',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptyText: {
    color: '#6b7280',
    textAlign: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  errorTitle: {
    color: '#dc2626',
    marginBottom: 8,
    textAlign: 'center',
  },
  errorText: {
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryLink: {
    color: '#3b82f6',
    fontWeight: '600',
  },
  // Job Radar styles
  radarButton: {
    marginLeft: 'auto',
    backgroundColor: '#3b82f6',
  },
  radarButtonLabel: {
    fontSize: 12,
  },
  radarBanner: {
    marginTop: 8,
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    padding: 12,
  },
  radarBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  radarBannerText: {
    marginLeft: 12,
    flex: 1,
  },
  radarStepNumber: {
    color: '#3b82f6',
    fontWeight: '600',
    marginBottom: 2,
  },
  radarStep: {
    color: '#1e40af',
  },
  radarProgress: {
    marginTop: 8,
    height: 4,
    borderRadius: 2,
  },
  radarCompleteBanner: {
    marginTop: 8,
    backgroundColor: '#dcfce7',
    borderRadius: 8,
    padding: 12,
  },
  radarCompleteContent: {
    flexDirection: 'column',
  },
  radarCompleteMain: {
    marginBottom: 8,
  },
  radarCompleteText: {
    color: '#166534',
    fontWeight: '600',
  },
  topMatchPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
    flexWrap: 'wrap',
  },
  topMatchLabel: {
    color: '#15803d',
    marginRight: 4,
  },
  topMatchTitle: {
    color: '#166534',
    flex: 1,
    fontWeight: '500',
  },
  topMatchScore: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginLeft: 8,
  },
  topMatchScoreText: {
    fontSize: 12,
    fontWeight: '600',
  },
  radarCompleteActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  viewAllLabel: {
    fontSize: 12,
    color: '#166534',
  },
  radarErrorBanner: {
    marginTop: 8,
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    padding: 12,
  },
  radarErrorContent: {
    marginBottom: 8,
  },
  radarErrorText: {
    color: '#dc2626',
    fontWeight: '500',
  },
  radarErrorHint: {
    color: '#b91c1c',
    marginTop: 4,
    fontSize: 12,
  },
  radarErrorActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 8,
  },
  retryButton: {
    backgroundColor: '#dc2626',
  },
  retryButtonLabel: {
    fontSize: 12,
    color: '#fff',
  },
  dismissLabel: {
    fontSize: 12,
  },
  // Modal styles
  modalContent: {
    backgroundColor: '#fff',
    margin: 20,
    borderRadius: 12,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  modalTitle: {
    color: '#111827',
  },
  modalClose: {
    fontSize: 24,
    color: '#6b7280',
    padding: 4,
  },
  modalStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  statItem: {
    alignItems: 'center',
  },
  statNumber: {
    color: '#3b82f6',
    fontWeight: '700',
  },
  statLabel: {
    color: '#6b7280',
    marginTop: 4,
  },
  scoreLegend: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 16,
    paddingVertical: 8,
    paddingHorizontal: 16,
    backgroundColor: '#f9fafb',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    color: '#6b7280',
    fontSize: 10,
  },
  matchesList: {
    maxHeight: 400,
  },
  matchItem: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  matchContent: {
    marginBottom: 12,
  },
  matchHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  matchTitle: {
    flex: 1,
    color: '#111827',
    fontWeight: '500',
  },
  matchCompany: {
    color: '#6b7280',
    marginTop: 4,
  },
  matchExplanation: {
    color: '#059669',
    marginTop: 8,
    lineHeight: 18,
    fontStyle: 'italic',
  },
  matchScore: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginLeft: 12,
  },
  scoreText: {
    fontWeight: '600',
  },
  matchActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
  },
  matchActionButton: {
    borderRadius: 6,
  },
  matchActionButtonDisabled: {
    opacity: 0.6,
  },
  matchActionLabel: {
    fontSize: 12,
    marginHorizontal: 4,
  },
  noMatches: {
    padding: 24,
    textAlign: 'center',
    color: '#6b7280',
  },
});
