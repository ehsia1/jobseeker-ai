import React, { useCallback } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { Text, Chip, SegmentedButtons } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useMatchesInfinite } from '../../src/hooks/useJobs';
import JobCard from '../../src/components/JobCard';
import type { JobMatch } from '@jobseeker/shared';

type StatusFilter = 'all' | 'saved' | 'applied' | 'interviewing';

export default function MatchesScreen() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>('all');

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
  } = useMatchesInfinite();

  const allMatches = data?.pages.flatMap((page) => page.items) ?? [];

  // Filter matches based on status
  const matches = statusFilter === 'all'
    ? allMatches
    : allMatches.filter((m) => m.status === statusFilter);

  const handleMatchPress = useCallback(
    (match: JobMatch) => {
      router.push(`/job/${match.job_id}`);
    },
    [router]
  );

  const handleApply = useCallback(
    (match: JobMatch) => {
      router.push(`/job/${match.job_id}?action=apply`);
    },
    [router]
  );

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const renderItem = useCallback(
    ({ item }: { item: JobMatch }) => (
      <View style={styles.matchCard}>
        <View style={styles.matchHeader}>
          <Chip
            style={[styles.statusChip, getStatusStyle(item.status)]}
            textStyle={styles.statusChipText}
          >
            {formatStatus(item.status)}
          </Chip>
          <Text variant="bodySmall" style={styles.matchDate}>
            Matched {formatDate(item.created_at)}
          </Text>
        </View>
        <JobCard
          job={item.job as any}
          onPress={() => handleMatchPress(item)}
          onApply={() => handleApply(item)}
          isSaved={true}
        />
        {item.notes && (
          <View style={styles.notesContainer}>
            <Text variant="bodySmall" style={styles.notesLabel}>
              Notes:
            </Text>
            <Text variant="bodySmall" style={styles.notesText}>
              {item.notes}
            </Text>
          </View>
        )}
      </View>
    ),
    [handleMatchPress, handleApply]
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
          No matches yet
        </Text>
        <Text variant="bodyMedium" style={styles.emptyText}>
          Save jobs from the Jobs tab to see them here
        </Text>
      </View>
    );
  }, [isLoading]);

  if (isError) {
    return (
      <View style={styles.errorContainer}>
        <Text variant="headlineSmall" style={styles.errorTitle}>
          Something went wrong
        </Text>
        <Text variant="bodyMedium" style={styles.errorText}>
          {error?.message || 'Failed to load matches'}
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
        <SegmentedButtons
          value={statusFilter}
          onValueChange={(value) => setStatusFilter(value as StatusFilter)}
          buttons={[
            { value: 'all', label: 'All' },
            { value: 'saved', label: 'Saved' },
            { value: 'applied', label: 'Applied' },
            { value: 'interviewing', label: 'Interview' },
          ]}
          style={styles.segmentedButtons}
        />
      </View>

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3b82f6" />
        </View>
      ) : (
        <FlatList
          data={matches}
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
        />
      )}
    </View>
  );
}

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    new: 'New',
    saved: 'Saved',
    applied: 'Applied',
    interviewing: 'Interviewing',
    rejected: 'Rejected',
    offered: 'Offered',
    accepted: 'Accepted',
  };
  return statusMap[status] || status;
}

function getStatusStyle(status: string) {
  const styles: Record<string, object> = {
    new: { backgroundColor: '#dbeafe' },
    saved: { backgroundColor: '#fef3c7' },
    applied: { backgroundColor: '#d1fae5' },
    interviewing: { backgroundColor: '#e0e7ff' },
    rejected: { backgroundColor: '#fee2e2' },
    offered: { backgroundColor: '#dcfce7' },
    accepted: { backgroundColor: '#bbf7d0' },
  };
  return styles[status] || { backgroundColor: '#f3f4f6' };
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  header: {
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  segmentedButtons: {
    backgroundColor: '#f3f4f6',
  },
  listContent: {
    padding: 16,
    paddingBottom: 32,
  },
  matchCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
  },
  matchHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 4,
  },
  statusChip: {
    height: 24,
  },
  statusChipText: {
    fontSize: 11,
    lineHeight: 14,
  },
  matchDate: {
    color: '#9ca3af',
  },
  notesContainer: {
    paddingHorizontal: 12,
    paddingBottom: 12,
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
    paddingTop: 8,
  },
  notesLabel: {
    color: '#6b7280',
    fontWeight: '600',
    marginBottom: 2,
  },
  notesText: {
    color: '#374151',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
