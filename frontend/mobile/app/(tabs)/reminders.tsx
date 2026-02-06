import React, { useCallback, useState } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { Text, Chip, Button, SegmentedButtons } from 'react-native-paper';
import { useRouter } from 'expo-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { remindersApi, type Reminder } from '../../src/api/client';

type ReminderFilter = 'all' | 'overdue' | 'upcoming';

export default function RemindersScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<ReminderFilter>('all');

  // Fetch reminders
  const {
    data: remindersData,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ['reminders'],
    queryFn: () => remindersApi.getReminders(false, false, 100),
  });

  // Complete reminder mutation
  const completeMutation = useMutation({
    mutationFn: (reminderId: string) => remindersApi.completeReminder(reminderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
    },
    onError: (err: Error) => {
      Alert.alert('Error', err.message || 'Failed to complete reminder');
    },
  });

  // Dismiss reminder mutation
  const dismissMutation = useMutation({
    mutationFn: (reminderId: string) => remindersApi.dismissReminder(reminderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
    },
    onError: (err: Error) => {
      Alert.alert('Error', err.message || 'Failed to dismiss reminder');
    },
  });

  // Filter reminders
  const reminders = remindersData?.reminders ?? [];
  const now = new Date();

  const filteredReminders = reminders.filter((r) => {
    const scheduledDate = new Date(r.scheduled_for);
    if (filter === 'overdue') {
      return scheduledDate < now && !r.is_completed && !r.is_dismissed;
    }
    if (filter === 'upcoming') {
      const hoursAhead = (scheduledDate.getTime() - now.getTime()) / (1000 * 60 * 60);
      return hoursAhead > 0 && hoursAhead <= 24;
    }
    return true;
  });

  const handleComplete = useCallback((reminder: Reminder) => {
    Alert.alert(
      'Complete Reminder',
      `Mark "${reminder.title}" as completed?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Complete',
          onPress: () => completeMutation.mutate(reminder.id),
        },
      ]
    );
  }, [completeMutation]);

  const handleDismiss = useCallback((reminder: Reminder) => {
    Alert.alert(
      'Dismiss Reminder',
      `Dismiss "${reminder.title}"? You can still view it later.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Dismiss',
          style: 'destructive',
          onPress: () => dismissMutation.mutate(reminder.id),
        },
      ]
    );
  }, [dismissMutation]);

  const handleViewJob = useCallback((reminder: Reminder) => {
    if (reminder.job_match_id) {
      // Navigate to the job via the match
      router.push(`/job/${reminder.job_match_id}`);
    }
  }, [router]);

  const renderItem = useCallback(
    ({ item }: { item: Reminder }) => {
      const scheduledDate = new Date(item.scheduled_for);
      const isOverdue = scheduledDate < now && !item.is_completed && !item.is_dismissed;
      const isUpcoming = !isOverdue && (scheduledDate.getTime() - now.getTime()) / (1000 * 60 * 60) <= 24;

      return (
        <TouchableOpacity
          style={[
            styles.reminderCard,
            isOverdue && styles.overdueCard,
            isUpcoming && styles.upcomingCard,
          ]}
          onPress={() => handleViewJob(item)}
          activeOpacity={0.7}
        >
          <View style={styles.reminderHeader}>
            <View style={styles.reminderChips}>
              <Chip
                style={[styles.typeChip, getTypeStyle(item.reminder_type)]}
                textStyle={styles.typeChipText}
              >
                {formatType(item.reminder_type)}
              </Chip>
              {isOverdue && (
                <Chip style={styles.overdueChip} textStyle={styles.overdueChipText}>
                  Overdue
                </Chip>
              )}
              {isUpcoming && !isOverdue && (
                <Chip style={styles.upcomingChip} textStyle={styles.upcomingChipText}>
                  Soon
                </Chip>
              )}
            </View>
            <Text variant="bodySmall" style={styles.date}>
              {formatDate(item.scheduled_for)}
            </Text>
          </View>

          <Text variant="titleMedium" style={styles.title}>
            {item.title}
          </Text>

          {item.company && (
            <Text variant="bodyMedium" style={styles.company}>
              {item.company}
            </Text>
          )}

          {item.description && (
            <Text variant="bodySmall" style={styles.description} numberOfLines={2}>
              {item.description}
            </Text>
          )}

          <View style={styles.actions}>
            <Button
              mode="contained"
              onPress={() => handleComplete(item)}
              style={styles.completeButton}
              labelStyle={styles.buttonLabel}
              compact
            >
              Complete
            </Button>
            <Button
              mode="outlined"
              onPress={() => handleDismiss(item)}
              style={styles.dismissButton}
              labelStyle={styles.dismissButtonLabel}
              compact
            >
              Dismiss
            </Button>
          </View>
        </TouchableOpacity>
      );
    },
    [handleComplete, handleDismiss, handleViewJob, now]
  );

  const renderEmpty = useCallback(() => {
    if (isLoading) return null;
    return (
      <View style={styles.emptyContainer}>
        <Text variant="headlineSmall" style={styles.emptyTitle}>
          No reminders
        </Text>
        <Text variant="bodyMedium" style={styles.emptyText}>
          {filter === 'overdue'
            ? "You're all caught up! No overdue reminders."
            : filter === 'upcoming'
            ? 'No reminders in the next 24 hours.'
            : 'Reminders will appear here when you apply to jobs.'}
        </Text>
      </View>
    );
  }, [isLoading, filter]);

  if (isError) {
    return (
      <View style={styles.errorContainer}>
        <Text variant="headlineSmall" style={styles.errorTitle}>
          Something went wrong
        </Text>
        <Text variant="bodyMedium" style={styles.errorText}>
          {error?.message || 'Failed to load reminders'}
        </Text>
        <Button mode="contained" onPress={() => refetch()}>
          Retry
        </Button>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Stats Header */}
      <View style={styles.header}>
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text variant="headlineMedium" style={[styles.statNumber, { color: '#dc2626' }]}>
              {remindersData?.overdue_count ?? 0}
            </Text>
            <Text variant="bodySmall" style={styles.statLabel}>Overdue</Text>
          </View>
          <View style={styles.statCard}>
            <Text variant="headlineMedium" style={[styles.statNumber, { color: '#f59e0b' }]}>
              {remindersData?.upcoming_count ?? 0}
            </Text>
            <Text variant="bodySmall" style={styles.statLabel}>Upcoming</Text>
          </View>
          <View style={styles.statCard}>
            <Text variant="headlineMedium" style={[styles.statNumber, { color: '#3b82f6' }]}>
              {remindersData?.total ?? 0}
            </Text>
            <Text variant="bodySmall" style={styles.statLabel}>Total</Text>
          </View>
        </View>

        <SegmentedButtons
          value={filter}
          onValueChange={(value) => setFilter(value as ReminderFilter)}
          buttons={[
            { value: 'all', label: 'All' },
            { value: 'overdue', label: 'Overdue' },
            { value: 'upcoming', label: 'Upcoming' },
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
          data={filteredReminders}
          renderItem={renderItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={refetch}
              tintColor="#3b82f6"
              colors={['#3b82f6']}
            />
          }
          ListEmptyComponent={renderEmpty}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

function formatType(type: string): string {
  const typeMap: Record<string, string> = {
    follow_up: 'Follow-up',
    interview_prep: 'Interview Prep',
    interview: 'Interview',
    deadline: 'Deadline',
    custom: 'Custom',
  };
  return typeMap[type] || type;
}

function getTypeStyle(type: string) {
  const styles: Record<string, object> = {
    follow_up: { backgroundColor: '#dbeafe' },
    interview_prep: { backgroundColor: '#fef3c7' },
    interview: { backgroundColor: '#d1fae5' },
    deadline: { backgroundColor: '#fee2e2' },
    custom: { backgroundColor: '#f3f4f6' },
  };
  return styles[type] || { backgroundColor: '#f3f4f6' };
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMs < 0) {
    // Past
    const absDays = Math.abs(diffDays);
    if (absDays === 0) return 'Today';
    if (absDays === 1) return 'Yesterday';
    return `${absDays} days ago`;
  } else {
    // Future
    if (diffHours < 1) return 'In less than an hour';
    if (diffHours < 24) return `In ${diffHours} hours`;
    if (diffDays === 1) return 'Tomorrow';
    return `In ${diffDays} days`;
  }
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
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 12,
  },
  statCard: {
    alignItems: 'center',
    padding: 8,
  },
  statNumber: {
    fontWeight: '700',
  },
  statLabel: {
    color: '#6b7280',
    marginTop: 2,
  },
  segmentedButtons: {
    backgroundColor: '#f3f4f6',
  },
  listContent: {
    padding: 16,
    paddingBottom: 32,
  },
  reminderCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#3b82f6',
  },
  overdueCard: {
    borderLeftColor: '#dc2626',
    backgroundColor: '#fef2f2',
  },
  upcomingCard: {
    borderLeftColor: '#f59e0b',
  },
  reminderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  reminderChips: {
    flexDirection: 'row',
    gap: 8,
  },
  typeChip: {
    height: 24,
  },
  typeChipText: {
    fontSize: 11,
    lineHeight: 14,
  },
  overdueChip: {
    backgroundColor: '#fee2e2',
    height: 24,
  },
  overdueChipText: {
    fontSize: 11,
    lineHeight: 14,
    color: '#dc2626',
  },
  upcomingChip: {
    backgroundColor: '#fef3c7',
    height: 24,
  },
  upcomingChipText: {
    fontSize: 11,
    lineHeight: 14,
    color: '#d97706',
  },
  date: {
    color: '#6b7280',
  },
  title: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 4,
  },
  company: {
    color: '#4b5563',
    marginBottom: 4,
  },
  description: {
    color: '#6b7280',
    marginBottom: 12,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  completeButton: {
    backgroundColor: '#10b981',
    flex: 1,
  },
  buttonLabel: {
    fontSize: 13,
  },
  dismissButton: {
    borderColor: '#d1d5db',
    flex: 1,
  },
  dismissButtonLabel: {
    fontSize: 13,
    color: '#6b7280',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
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
});
