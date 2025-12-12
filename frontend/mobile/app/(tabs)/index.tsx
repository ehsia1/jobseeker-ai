import React, { useCallback, useState, useMemo } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Text, Searchbar, Chip } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useJobsInfinite, useMatchesInfinite, useSaveJob } from '../../src/hooks/useJobs';
import JobCard from '../../src/components/JobCard';
import type { ScoredJob } from '@jobseeker/shared';

export default function JobFeedScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);

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
        </View>
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
});
