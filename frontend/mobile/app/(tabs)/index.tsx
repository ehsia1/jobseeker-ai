import React, { useCallback, useState, useMemo } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
} from 'react-native';
import { Text, Searchbar, Chip, ProgressBar, Button, Portal, Modal } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useJobsInfinite, useMatchesInfinite, useSaveJob } from '../../src/hooks/useJobs';
import { useJobRadar } from '../../src/hooks/useAgent';
import JobCard from '../../src/components/JobCard';
import type { ScoredJob, JobRadarMatch } from '@jobseeker/shared';

export default function JobFeedScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [radarModalVisible, setRadarModalVisible] = useState(false);

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
  } = useJobsInfinite({ remote_only: remoteOnly });

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
    (job: ScoredJob) => {
      router.push(`/job/${job.id}`);
    },
    [router]
  );

  const handleSave = useCallback((job: ScoredJob) => {
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

  const handleApply = useCallback((job: ScoredJob) => {
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
    ({ item }: { item: ScoredJob }) => (
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
        <View style={styles.filters}>
          <Chip
            selected={remoteOnly}
            onPress={() => setRemoteOnly(!remoteOnly)}
            style={styles.chip}
            textStyle={styles.chipText}
            showSelectedOverlay
          >
            Remote Only
          </Chip>
          <Button
            mode="contained"
            onPress={handleRunRadar}
            disabled={jobRadar.isRunning}
            style={styles.radarButton}
            labelStyle={styles.radarButtonLabel}
            icon="radar"
            compact
          >
            {jobRadar.isRunning ? 'Scanning...' : 'Job Radar'}
          </Button>
        </View>

        {/* Job Radar Progress Banner */}
        {jobRadar.isRunning && (
          <View style={styles.radarBanner}>
            <View style={styles.radarBannerContent}>
              <ActivityIndicator size="small" color="#3b82f6" />
              <View style={styles.radarBannerText}>
                <Text variant="bodySmall" style={styles.radarStep}>
                  {jobRadar.currentStep || 'Starting radar scan...'}
                </Text>
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
          >
            <Text variant="bodyMedium" style={styles.radarCompleteText}>
              Found {jobRadar.result.matches_found} matches! Tap to view
            </Text>
            <Button
              mode="text"
              onPress={() => jobRadar.reset()}
              compact
              labelStyle={styles.dismissLabel}
            >
              Dismiss
            </Button>
          </TouchableOpacity>
        )}

        {/* Job Radar Error Banner */}
        {jobRadar.isFailed && (
          <View style={styles.radarErrorBanner}>
            <Text variant="bodySmall" style={styles.radarErrorText}>
              Radar scan failed: {jobRadar.errors[0] || 'Unknown error'}
            </Text>
            <Button
              mode="text"
              onPress={() => jobRadar.reset()}
              compact
              labelStyle={styles.dismissLabel}
            >
              Dismiss
            </Button>
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
            <TouchableOpacity onPress={() => setRadarModalVisible(false)}>
              <Text style={styles.modalClose}>✕</Text>
            </TouchableOpacity>
          </View>

          {jobRadar.result && (
            <>
              <View style={styles.modalStats}>
                <View style={styles.statItem}>
                  <Text variant="headlineMedium" style={styles.statNumber}>
                    {jobRadar.result.jobs_found}
                  </Text>
                  <Text variant="bodySmall" style={styles.statLabel}>
                    Jobs Scanned
                  </Text>
                </View>
                <View style={styles.statItem}>
                  <Text variant="headlineMedium" style={styles.statNumber}>
                    {jobRadar.result.matches_found}
                  </Text>
                  <Text variant="bodySmall" style={styles.statLabel}>
                    Matches
                  </Text>
                </View>
              </View>

              <FlatList
                data={jobRadar.result.top_matches}
                keyExtractor={(item) => item.job_id}
                style={styles.matchesList}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.matchItem}
                    onPress={() => handleRadarJobPress(item)}
                  >
                    <View style={styles.matchInfo}>
                      <Text variant="bodyLarge" style={styles.matchTitle} numberOfLines={1}>
                        {item.title}
                      </Text>
                      <Text variant="bodySmall" style={styles.matchCompany} numberOfLines={1}>
                        {item.company} {item.location && `• ${item.location}`}
                        {item.remote && ' • Remote'}
                      </Text>
                    </View>
                    <View style={styles.matchScore}>
                      <Text variant="titleMedium" style={styles.scoreText}>
                        {item.score}%
                      </Text>
                    </View>
                  </TouchableOpacity>
                )}
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
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  radarCompleteText: {
    color: '#166534',
    flex: 1,
  },
  radarErrorBanner: {
    marginTop: 8,
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  radarErrorText: {
    color: '#dc2626',
    flex: 1,
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
  matchesList: {
    maxHeight: 400,
  },
  matchItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  matchInfo: {
    flex: 1,
  },
  matchTitle: {
    color: '#111827',
    fontWeight: '500',
  },
  matchCompany: {
    color: '#6b7280',
    marginTop: 2,
  },
  matchScore: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginLeft: 12,
  },
  scoreText: {
    color: '#1d4ed8',
    fontWeight: '600',
  },
  noMatches: {
    padding: 24,
    textAlign: 'center',
    color: '#6b7280',
  },
});
