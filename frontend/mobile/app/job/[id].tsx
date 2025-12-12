import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Linking,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import {
  Text,
  Button,
  Chip,
  Divider,
  Surface,
  TextInput,
} from 'react-native-paper';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useJob, useMatchesInfinite, useSaveJob } from '../../src/hooks/useJobs';
import { ScoreBreakdownBar } from '../../src/components/ScoreBadge';
import { matchesApi, proposalsApi } from '../../src/api/client';
import type { ScoredJob, MatchStatus } from '@jobseeker/shared';

export default function JobDetailsScreen() {
  const { id, action } = useLocalSearchParams<{ id: string; action?: string }>();
  const router = useRouter();
  const { data: job, isLoading, isError, error } = useJob(id);

  // Fetch matches to check if job is saved
  const { data: matchesData } = useMatchesInfinite();
  const saveJobMutation = useSaveJob();

  const [showProposalModal, setShowProposalModal] = useState(false);
  const [proposal, setProposal] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  // Find the match for this job if it exists
  const existingMatch = useMemo(() => {
    const allMatches = matchesData?.pages.flatMap((page) => page.items) ?? [];
    return allMatches.find((match) => match.job_id === id);
  }, [matchesData, id]);

  const isSaved = !!existingMatch;

  useEffect(() => {
    if (action === 'apply' && job) {
      setShowProposalModal(true);
    }
  }, [action, job]);

  const handleSave = () => {
    if (!job) return;

    if (isSaved) {
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
  };

  const handleApply = async () => {
    setShowProposalModal(true);
  };

  const handleGenerateProposal = async () => {
    if (!job) return;
    setIsGenerating(true);
    try {
      const result = await proposalsApi.generate(job.id, 'medium');
      setProposal(result.proposal);
    } catch (err) {
      console.error('Failed to generate proposal:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyProposal = async () => {
    // Using expo-clipboard would be better, but for now just alert
    // In production: await Clipboard.setStringAsync(proposal);
    console.log('Copy proposal:', proposal);
  };

  const handleMarkApplied = async () => {
    if (!job) return;
    try {
      if (existingMatch) {
        await matchesApi.updateStatus(existingMatch.id, 'applied');
      } else {
        const match = await matchesApi.create(job.id);
        await matchesApi.updateStatus(match.id, 'applied');
      }
      setShowProposalModal(false);
      Alert.alert('Success', 'Job marked as applied!');
      router.back();
    } catch (err) {
      console.error('Failed to mark as applied:', err);
      Alert.alert('Error', 'Failed to mark as applied. Please try again.');
    }
  };

  const handleOpenExternal = () => {
    if (job?.url) {
      Linking.openURL(job.url);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }

  if (isError || !job) {
    return (
      <View style={styles.errorContainer}>
        <Text variant="headlineSmall" style={styles.errorTitle}>
          Job not found
        </Text>
        <Text variant="bodyMedium" style={styles.errorText}>
          {error?.message || 'Unable to load job details'}
        </Text>
        <Button mode="contained" onPress={() => router.back()}>
          Go Back
        </Button>
      </View>
    );
  }

  const scored = 'total_score' in job;
  const scoredJob = job as ScoredJob;

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Job Details',
          headerRight: () => (
            <Ionicons
              name="open-outline"
              size={22}
              color="#3b82f6"
              onPress={handleOpenExternal}
              style={{ marginRight: 8 }}
            />
          ),
        }}
      />
      <ScrollView style={styles.container}>
        {/* Header */}
        <Surface style={styles.headerCard}>
          <View style={styles.headerRow}>
            <View style={styles.headerText}>
              <Text variant="headlineSmall" style={styles.title}>
                {job.title}
              </Text>
              <Text variant="titleMedium" style={styles.company}>
                {job.company}
              </Text>
            </View>
            {scored && (
              <View
                style={[
                  styles.scoreBadge,
                  { backgroundColor: getScoreColor(scoredJob.total_score) },
                ]}
              >
                <Text style={styles.scoreText}>
                  {Math.round(scoredJob.total_score)}
                </Text>
                <Text style={styles.scoreLabel}>Match</Text>
              </View>
            )}
          </View>

          {/* Tags */}
          <View style={styles.tags}>
            {job.remote && (
              <Chip icon="wifi" style={styles.chip}>
                Remote
              </Chip>
            )}
            {job.location && (
              <Chip icon="map-marker" style={styles.chip}>
                {job.location}
              </Chip>
            )}
            {(job.rate_min || job.rate_max) && (
              <Chip icon="currency-usd" style={styles.chip}>
                {formatRate(job.rate_min, job.rate_max, job.rate_type)}
              </Chip>
            )}
            {job.hours_per_week && (
              <Chip icon="clock-outline" style={styles.chip}>
                {job.hours_per_week}h/week
              </Chip>
            )}
          </View>

          {/* Posted date */}
          <Text variant="bodySmall" style={styles.postedDate}>
            Posted {formatDate(job.posted_at)}
          </Text>
        </Surface>

        {/* Score Breakdown */}
        {scored && scoredJob.score_breakdown && (
          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Match Score Breakdown
            </Text>
            <View style={styles.scoreBreakdown}>
              {Object.entries(scoredJob.score_breakdown).map(([key, value]) => (
                <ScoreBreakdownBar
                  key={key}
                  label={formatScoreKey(key)}
                  score={value}
                  maxScore={100}
                />
              ))}
            </View>
          </Surface>
        )}

        {/* Description */}
        <Surface style={styles.section}>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Description
          </Text>
          <Text variant="bodyMedium" style={styles.description}>
            {job.description || 'No description available'}
          </Text>
        </Surface>

        {/* Requirements */}
        {job.requirements && (
          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Requirements
            </Text>
            <Text variant="bodyMedium" style={styles.description}>
              {job.requirements}
            </Text>
          </Surface>
        )}

        {/* Skills */}
        {job.skills && job.skills.length > 0 && (
          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Required Skills
            </Text>
            <View style={styles.skillsContainer}>
              {job.skills.map((skill, index) => (
                <Chip key={index} style={styles.skillChip}>
                  {skill}
                </Chip>
              ))}
            </View>
          </Surface>
        )}

        {/* Spacer for bottom buttons */}
        <View style={{ height: 100 }} />
      </ScrollView>

      {/* Bottom Action Bar */}
      <Surface style={styles.bottomBar}>
        <Button
          mode={isSaved ? 'contained' : 'outlined'}
          onPress={handleSave}
          loading={saveJobMutation.isPending}
          disabled={isSaved}
          style={[styles.bottomButton, isSaved && styles.savedButton]}
          icon={isSaved ? 'bookmark' : 'bookmark-outline'}
        >
          {isSaved ? 'Saved' : 'Save'}
        </Button>
        <Button
          mode="contained"
          onPress={handleApply}
          style={[styles.bottomButton, styles.applyButton]}
          icon="send"
        >
          Apply
        </Button>
      </Surface>

      {/* Proposal Overlay - using View instead of Portal/Modal to fix z-index in modal screens */}
      {showProposalModal && (
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => setShowProposalModal(false)}
          />
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.modalKeyboardView}
          >
            <Surface style={styles.modalContainer}>
              <Text variant="titleLarge" style={styles.modalTitle}>
                Generate Proposal
              </Text>
              <Text variant="bodyMedium" style={styles.modalSubtitle}>
                Generate a custom proposal for this job using AI
              </Text>

              {proposal ? (
                <>
                  <ScrollView style={styles.proposalScroll}>
                    <TextInput
                      value={proposal}
                      onChangeText={setProposal}
                      multiline
                      numberOfLines={10}
                      style={styles.proposalInput}
                      mode="outlined"
                    />
                  </ScrollView>
                  <View style={styles.modalActions}>
                    <Button
                      mode="outlined"
                      onPress={handleCopyProposal}
                      icon="content-copy"
                      style={styles.modalButton}
                    >
                      Copy
                    </Button>
                    <Button
                      mode="contained"
                      onPress={handleMarkApplied}
                      icon="check"
                      style={styles.modalButton}
                    >
                      Mark Applied
                    </Button>
                  </View>
                </>
              ) : (
                <View style={styles.generateContainer}>
                  <Button
                    mode="contained"
                    onPress={handleGenerateProposal}
                    loading={isGenerating}
                    disabled={isGenerating}
                    icon="auto-fix"
                  >
                    {isGenerating ? 'Generating...' : 'Generate Proposal'}
                  </Button>
                </View>
              )}

              <Button
                mode="text"
                onPress={() => setShowProposalModal(false)}
                style={styles.closeButton}
              >
                Close
              </Button>
            </Surface>
          </KeyboardAvoidingView>
        </View>
      )}
    </>
  );
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#eab308';
  return '#6b7280';
}

function formatRate(min?: number, max?: number, type?: string): string {
  if (!min && !max) return '';
  const rateType = type === 'hourly' ? '/hr' : type === 'fixed' ? ' fixed' : '';
  if (min && max) return `$${min}-$${max}${rateType}`;
  if (min) return `$${min}+${rateType}`;
  return `Up to $${max}${rateType}`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatScoreKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorTitle: {
    color: '#dc2626',
    marginBottom: 8,
  },
  errorText: {
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 16,
  },
  headerCard: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  headerText: {
    flex: 1,
    marginRight: 12,
  },
  title: {
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  company: {
    color: '#6b7280',
  },
  scoreBadge: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scoreText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 20,
  },
  scoreLabel: {
    color: '#fff',
    fontSize: 10,
    opacity: 0.9,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 16,
  },
  chip: {
    backgroundColor: '#f3f4f6',
  },
  postedDate: {
    color: '#9ca3af',
    marginTop: 12,
  },
  section: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  sectionTitle: {
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  description: {
    color: '#374151',
    lineHeight: 22,
  },
  scoreBreakdown: {
    gap: 12,
  },
  skillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    backgroundColor: '#e0e7ff',
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    padding: 16,
    paddingBottom: 32,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    gap: 12,
  },
  bottomButton: {
    flex: 1,
  },
  savedButton: {
    backgroundColor: '#22c55e',
  },
  applyButton: {
    flex: 2,
  },
  modalOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalKeyboardView: {
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContainer: {
    backgroundColor: '#fff',
    marginHorizontal: 20,
    padding: 20,
    borderRadius: 12,
    maxHeight: '80%',
    width: '90%',
    elevation: 5,
  },
  modalTitle: {
    fontWeight: '700',
    marginBottom: 4,
  },
  modalSubtitle: {
    color: '#6b7280',
    marginBottom: 20,
  },
  proposalScroll: {
    maxHeight: 300,
    marginBottom: 16,
  },
  proposalInput: {
    backgroundColor: '#f9fafb',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
  },
  modalButton: {
    flex: 1,
  },
  generateContainer: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  closeButton: {
    marginTop: 12,
  },
});
