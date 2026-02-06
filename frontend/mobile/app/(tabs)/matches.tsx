import React, { useCallback, useState } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { Text, Chip, SegmentedButtons, Button, Portal, Modal, ProgressBar } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useMatchesInfinite, useUpdateMatchStatus } from '../../src/hooks/useJobs';
import { useApplicationTracker } from '../../src/hooks/useAgent';
import JobCard from '../../src/components/JobCard';
import type { JobMatch, TrackerActionItem, TrackerRecommendation, JobMatchStatus } from '@jobseeker/shared';

type StatusFilter = 'all' | 'saved' | 'applied' | 'interviewing';

export default function MatchesScreen() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>('all');
  const [briefingModalVisible, setBriefingModalVisible] = useState(false);

  // Application Tracker agent for briefings
  const applicationTracker = useApplicationTracker();

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

  // Status update mutation
  const updateStatusMutation = useUpdateMatchStatus();

  const handleStatusUpdate = useCallback(
    (match: JobMatch, newStatus: JobMatchStatus, confirmMessage?: string) => {
      const doUpdate = () => {
        updateStatusMutation.mutate(
          { matchId: match.id, status: newStatus },
          {
            onSuccess: () => {
              refetch();
            },
            onError: (err) => {
              Alert.alert('Error', err.message || 'Failed to update status');
            },
          }
        );
      };

      if (confirmMessage) {
        Alert.alert('Update Status', confirmMessage, [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Confirm', onPress: doUpdate },
        ]);
      } else {
        doUpdate();
      }
    },
    [updateStatusMutation, refetch]
  );

  // Get next status options based on current status
  const getStatusActions = (status: string): { label: string; status: JobMatchStatus; style: 'success' | 'danger' | 'neutral' }[] => {
    switch (status) {
      case 'saved':
        return [
          { label: 'Mark Applied', status: 'applied', style: 'success' },
          { label: 'Not Interested', status: 'rejected', style: 'danger' },
        ];
      case 'applied':
        return [
          { label: 'Got Interview!', status: 'interviewing', style: 'success' },
          { label: 'Rejected', status: 'rejected', style: 'danger' },
        ];
      case 'interviewing':
        return [
          { label: 'Got Offer!', status: 'offer_received' as JobMatchStatus, style: 'success' },
          { label: 'Rejected', status: 'rejected', style: 'danger' },
        ];
      default:
        return [];
    }
  };

  // Run Application Tracker briefing
  const handleGetBriefing = useCallback(() => {
    setBriefingModalVisible(true);
    applicationTracker.run({});
  }, [applicationTracker]);

  // Navigate to job from action item
  const handleActionItemPress = useCallback(
    (item: TrackerActionItem) => {
      setBriefingModalVisible(false);
      if (item.application_id) {
        // Could navigate to application details if needed
        router.push(`/matches`);
      }
    },
    [router]
  );

  // Get color based on priority
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return '#dc2626';
      case 'medium':
        return '#f59e0b';
      case 'low':
        return '#10b981';
      default:
        return '#6b7280';
    }
  };

  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const renderItem = useCallback(
    ({ item }: { item: JobMatch }) => {
      const statusActions = getStatusActions(item.status);

      return (
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
          {item.client_notes && (
            <View style={styles.notesContainer}>
              <Text variant="bodySmall" style={styles.notesLabel}>
                Notes:
              </Text>
              <Text variant="bodySmall" style={styles.notesText}>
                {item.client_notes}
              </Text>
            </View>
          )}
          {/* Status Progression Buttons */}
          {statusActions.length > 0 && (
            <View style={styles.statusActionsContainer}>
              {statusActions.map((action) => (
                <Button
                  key={action.status}
                  mode={action.style === 'success' ? 'contained' : 'outlined'}
                  onPress={() => handleStatusUpdate(
                    item,
                    action.status,
                    action.style === 'danger' ? `Mark this job as ${action.label.toLowerCase()}?` : undefined
                  )}
                  style={[
                    styles.statusActionButton,
                    action.style === 'success' && styles.successButton,
                    action.style === 'danger' && styles.dangerButton,
                  ]}
                  labelStyle={[
                    styles.statusActionLabel,
                    action.style === 'danger' && styles.dangerLabel,
                  ]}
                  compact
                  disabled={updateStatusMutation.isPending}
                >
                  {action.label}
                </Button>
              ))}
            </View>
          )}
        </View>
      );
    },
    [handleMatchPress, handleApply, handleStatusUpdate, updateStatusMutation.isPending]
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
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.tabsScrollContent}
        >
          <SegmentedButtons
            value={statusFilter}
            onValueChange={(value) => setStatusFilter(value as StatusFilter)}
            buttons={[
              { value: 'all', label: 'All' },
              { value: 'saved', label: 'Saved' },
              { value: 'applied', label: 'Applied' },
              { value: 'interviewing', label: 'Interviewing' },
            ]}
            style={styles.segmentedButtons}
          />
        </ScrollView>
        <View style={styles.headerRow}>
          <Button
            mode="contained"
            onPress={handleGetBriefing}
            disabled={applicationTracker.isRunning}
            style={styles.briefingButton}
            labelStyle={styles.briefingButtonLabel}
            icon="clipboard-text"
            compact
          >
            {applicationTracker.isRunning ? 'Loading...' : 'Get Application Briefing'}
          </Button>
        </View>

        {/* Briefing Progress Banner */}
        {applicationTracker.isRunning && (
          <View style={styles.briefingBanner}>
            <View style={styles.briefingBannerContent}>
              <ActivityIndicator size="small" color="#3b82f6" />
              <View style={styles.briefingBannerText}>
                <Text variant="bodySmall" style={styles.briefingStep}>
                  {applicationTracker.currentStep || 'Analyzing your applications...'}
                </Text>
              </View>
            </View>
            <ProgressBar
              progress={applicationTracker.progress / 100}
              color="#3b82f6"
              style={styles.briefingProgress}
            />
          </View>
        )}
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

      {/* Application Tracker Briefing Modal */}
      <Portal>
        <Modal
          visible={briefingModalVisible}
          onDismiss={() => setBriefingModalVisible(false)}
          contentContainerStyle={styles.modalContent}
        >
          <View style={styles.modalHeader}>
            <Text variant="titleLarge" style={styles.modalTitle}>
              Application Briefing
            </Text>
            <TouchableOpacity onPress={() => setBriefingModalVisible(false)}>
              <Text style={styles.modalClose}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalScroll}>
            {/* Loading State */}
            {applicationTracker.isRunning && (
              <View style={styles.modalLoadingContainer}>
                <ActivityIndicator size="large" color="#3b82f6" />
                <Text variant="bodyMedium" style={styles.modalLoadingText}>
                  {applicationTracker.currentStep || 'Analyzing your applications...'}
                </Text>
                <ProgressBar
                  progress={applicationTracker.progress / 100}
                  color="#3b82f6"
                  style={styles.modalProgressBar}
                />
              </View>
            )}

            {/* Error State */}
            {applicationTracker.isFailed && (
              <View style={styles.modalErrorContainer}>
                <Text variant="bodyLarge" style={styles.modalErrorTitle}>
                  Analysis Failed
                </Text>
                <Text variant="bodySmall" style={styles.modalErrorText}>
                  {applicationTracker.errors[0] || 'Unknown error occurred'}
                </Text>
                <Button
                  mode="contained"
                  onPress={() => applicationTracker.run({})}
                  style={styles.retryButton}
                >
                  Try Again
                </Button>
              </View>
            )}

            {/* Results State */}
            {applicationTracker.isCompleted && applicationTracker.result && (
              <>
                {/* Briefing Text */}
                {applicationTracker.result.briefing && (
                  <View style={styles.briefingSection}>
                    <Text variant="bodyMedium" style={styles.briefingText}>
                      {applicationTracker.result.briefing}
                    </Text>
                  </View>
                )}

                {/* Summary Stats */}
                <View style={styles.summarySection}>
                  <Text variant="titleMedium" style={styles.sectionTitle}>
                    Summary
                  </Text>
                  <View style={styles.statsGrid}>
                    <View style={styles.statCard}>
                      <Text variant="headlineMedium" style={styles.statNumber}>
                        {applicationTracker.result.stats?.total_applications ?? 0}
                      </Text>
                      <Text variant="bodySmall" style={styles.statLabel}>
                        Total
                      </Text>
                    </View>
                    <View style={styles.statCard}>
                      <Text variant="headlineMedium" style={[styles.statNumber, { color: '#f59e0b' }]}>
                        {applicationTracker.result.stats?.active_applications ?? 0}
                      </Text>
                      <Text variant="bodySmall" style={styles.statLabel}>
                        Active
                      </Text>
                    </View>
                    <View style={styles.statCard}>
                      <Text variant="headlineMedium" style={[styles.statNumber, { color: '#10b981' }]}>
                        {applicationTracker.result.portfolio_analysis?.interview_count ?? 0}
                      </Text>
                      <Text variant="bodySmall" style={styles.statLabel}>
                        Interviews
                      </Text>
                    </View>
                    <View style={styles.statCard}>
                      <Text variant="headlineMedium" style={[styles.statNumber, { color: '#dc2626' }]}>
                        {applicationTracker.result.stale_applications?.length ?? 0}
                      </Text>
                      <Text variant="bodySmall" style={styles.statLabel}>
                        Stale
                      </Text>
                    </View>
                  </View>
                </View>

                {/* Action Items */}
                {applicationTracker.result.action_items?.length > 0 && (
                  <View style={styles.actionItemsSection}>
                    <Text variant="titleMedium" style={styles.sectionTitle}>
                      Action Items
                    </Text>
                    {applicationTracker.result.action_items.map((item: TrackerActionItem, index: number) => (
                      <TouchableOpacity
                        key={`${item.application_id || index}-${index}`}
                        style={styles.actionItem}
                        onPress={() => handleActionItemPress(item)}
                      >
                        <View style={styles.actionItemContent}>
                          <View style={styles.actionItemHeader}>
                            <Chip
                              style={[
                                styles.priorityChip,
                                { backgroundColor: `${getPriorityColor(item.priority)}20` },
                              ]}
                              textStyle={[
                                styles.priorityChipText,
                                { color: getPriorityColor(item.priority) },
                              ]}
                            >
                              {item.priority}
                            </Chip>
                            <Chip
                              style={styles.typeChip}
                              textStyle={styles.typeChipText}
                            >
                              {item.type}
                            </Chip>
                          </View>
                          <Text variant="bodyMedium" style={styles.actionItemTitle}>
                            {item.title}
                          </Text>
                          <Text variant="bodySmall" style={styles.actionItemAction}>
                            {item.description}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    ))}
                  </View>
                )}

                {/* Insights */}
                {(applicationTracker.result.portfolio_analysis?.insights?.length ?? 0) > 0 && (
                  <View style={styles.insightsSection}>
                    <Text variant="titleMedium" style={styles.sectionTitle}>
                      Insights
                    </Text>
                    {applicationTracker.result.portfolio_analysis?.insights.map((insight: string, index: number) => (
                      <View key={index} style={styles.insightItem}>
                        <Text style={styles.insightBullet}>•</Text>
                        <Text variant="bodySmall" style={styles.insightText}>
                          {insight}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}

                {/* Recommendations */}
                {applicationTracker.result.recommendations?.length > 0 && (
                  <View style={styles.insightsSection}>
                    <Text variant="titleMedium" style={styles.sectionTitle}>
                      Recommendations
                    </Text>
                    {applicationTracker.result.recommendations.map((rec: TrackerRecommendation, index: number) => (
                      <View key={index} style={styles.recommendationItem}>
                        <Chip
                          style={[
                            styles.priorityChip,
                            { backgroundColor: `${getPriorityColor(rec.priority)}20` },
                          ]}
                          textStyle={[
                            styles.priorityChipText,
                            { color: getPriorityColor(rec.priority) },
                          ]}
                        >
                          {rec.priority}
                        </Chip>
                        <Text variant="bodyMedium" style={styles.recommendationTitle}>
                          {rec.title}
                        </Text>
                        <Text variant="bodySmall" style={styles.recommendationDescription}>
                          {rec.description}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </>
            )}
          </ScrollView>
        </Modal>
      </Portal>
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
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
  },
  tabsScrollContent: {
    flexGrow: 1,
  },
  segmentedButtons: {
    backgroundColor: '#f3f4f6',
  },
  briefingButton: {
    backgroundColor: '#3b82f6',
  },
  briefingButtonLabel: {
    fontSize: 13,
  },
  briefingBanner: {
    marginTop: 8,
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    padding: 12,
  },
  briefingBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  briefingBannerText: {
    marginLeft: 12,
    flex: 1,
  },
  briefingStep: {
    color: '#1e40af',
  },
  briefingProgress: {
    marginTop: 8,
    height: 4,
    borderRadius: 2,
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
  // Modal styles
  modalContent: {
    backgroundColor: '#fff',
    margin: 20,
    borderRadius: 12,
    maxHeight: '85%',
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
  modalScroll: {
    maxHeight: 500,
  },
  modalLoadingContainer: {
    padding: 32,
    alignItems: 'center',
  },
  modalLoadingText: {
    color: '#6b7280',
    marginTop: 16,
    marginBottom: 16,
    textAlign: 'center',
  },
  modalProgressBar: {
    width: '100%',
    height: 4,
    borderRadius: 2,
  },
  modalErrorContainer: {
    padding: 32,
    alignItems: 'center',
  },
  modalErrorTitle: {
    color: '#dc2626',
    fontWeight: '600',
    marginBottom: 8,
  },
  modalErrorText: {
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    backgroundColor: '#3b82f6',
  },
  // Summary section
  summarySection: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  sectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 12,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    marginBottom: 8,
  },
  statNumber: {
    color: '#3b82f6',
    fontWeight: '700',
  },
  statLabel: {
    color: '#6b7280',
    marginTop: 4,
  },
  // Action items section
  actionItemsSection: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  actionItem: {
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    marginBottom: 8,
    overflow: 'hidden',
  },
  actionItemContent: {
    padding: 12,
  },
  actionItemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  priorityChip: {
    height: 24,
  },
  priorityChipText: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  dueDate: {
    color: '#6b7280',
  },
  actionItemTitle: {
    color: '#111827',
    fontWeight: '500',
    marginBottom: 2,
  },
  actionItemCompany: {
    color: '#6b7280',
    marginBottom: 4,
  },
  actionItemAction: {
    color: '#374151',
    fontStyle: 'italic',
  },
  // Insights section
  insightsSection: {
    padding: 16,
  },
  insightItem: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  insightBullet: {
    color: '#3b82f6',
    marginRight: 8,
    fontSize: 16,
  },
  insightText: {
    color: '#374151',
    flex: 1,
  },
  // Briefing section
  briefingSection: {
    padding: 16,
    backgroundColor: '#f0f9ff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  briefingText: {
    color: '#1e40af',
    lineHeight: 22,
  },
  // Type chip for action items
  typeChip: {
    height: 24,
    marginLeft: 8,
  },
  typeChipText: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  // Recommendations section
  recommendationsSection: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  recommendationItem: {
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#10b981',
  },
  recommendationTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 4,
  },
  recommendationDescription: {
    color: '#6b7280',
    lineHeight: 20,
  },
  // Status action buttons
  statusActionsContainer: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingHorizontal: 12,
    paddingBottom: 12,
    gap: 8,
  },
  statusActionButton: {
    minWidth: 100,
  },
  statusActionLabel: {
    fontSize: 12,
  },
  successButton: {
    backgroundColor: '#10b981',
  },
  dangerButton: {
    borderColor: '#dc2626',
  },
  dangerLabel: {
    color: '#dc2626',
  },
});
