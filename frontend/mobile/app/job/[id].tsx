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
import * as Clipboard from 'expo-clipboard';
import {
  Text,
  Button,
  Chip,
  Divider,
  Surface,
  TextInput,
  ProgressBar,
  Menu,
  FAB,
} from 'react-native-paper';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useJob, useMatchesInfinite, useSaveJob, useUpdateMatchStatus } from '../../src/hooks/useJobs';
import { useCoverLetter, useInterviewPrep, useSalaryResearch, useSkillGap, useNetworkIntelligence, useAutoApply } from '../../src/hooks/useAgent';
import { ScoreBreakdownBar } from '../../src/components/ScoreBadge';
import { AgentLoadingState } from '../../src/components/AgentLoadingState';
import { ProposalABTest } from '../../src/components/ProposalABTest';
import { ClientRiskCard } from '../../src/components/ClientRiskCard';
import { matchesApi, proposalsApi } from '../../src/api/client';
import type { ScoredJob, JobMatchStatus, InterviewQuestion, SalaryRange, SkillGapItem, CoverLetterStyle } from '@jobseeker/shared';

export default function JobDetailsScreen() {
  const { id, action } = useLocalSearchParams<{ id: string; action?: string }>();
  const router = useRouter();
  const { data: job, isLoading, isError, error } = useJob(id);

  // Fetch matches to check if job is saved
  const { data: matchesData } = useMatchesInfinite();
  const saveJobMutation = useSaveJob();
  const updateStatusMutation = useUpdateMatchStatus();

  const [showProposalModal, setShowProposalModal] = useState(false);
  const [showInterviewPrepModal, setShowInterviewPrepModal] = useState(false);
  const [showSalaryModal, setShowSalaryModal] = useState(false);
  const [showSkillGapModal, setShowSkillGapModal] = useState(false);
  const [showNetworkModal, setShowNetworkModal] = useState(false);
  const [showAutoApplyModal, setShowAutoApplyModal] = useState(false);
  const [proposal, setProposal] = useState('');
  const [keyPoints, setKeyPoints] = useState<string[]>([]);
  const [coverLetterStyle, setCoverLetterStyle] = useState<CoverLetterStyle>('modern');
  const [styleMenuVisible, setStyleMenuVisible] = useState(false);
  const [proposalMode, setProposalMode] = useState<'single' | 'ab'>('single');
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(null);
  const [fabOpen, setFabOpen] = useState(false);

  // Cover Letter agent
  const coverLetter = useCoverLetter();

  // Interview Prep agent
  const interviewPrep = useInterviewPrep();

  // Salary Research agent
  const salaryResearch = useSalaryResearch();

  // Skill Gap agent
  const skillGap = useSkillGap();

  // Network Intelligence agent
  const networkIntel = useNetworkIntelligence();

  // Auto-Apply agent
  const autoApply = useAutoApply();

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
    // Use Cover Letter agent for sophisticated generation
    coverLetter.run({
      job_id: job.id,
      style: coverLetterStyle,
    });
  };

  // When cover letter is completed, update the proposal text and key points
  useEffect(() => {
    if (coverLetter.isCompleted && coverLetter.result?.result?.cover_letter) {
      setProposal(coverLetter.result.result.cover_letter);
      // Use keywords_used as key points to highlight
      if (coverLetter.result.result.keywords_used) {
        setKeyPoints(coverLetter.result.result.keywords_used);
      }
    }
  }, [coverLetter.isCompleted, coverLetter.result]);

  const handleCopyProposal = async () => {
    if (!proposal) {
      Alert.alert('Nothing to copy', 'Generate a cover letter first.');
      return;
    }
    try {
      await Clipboard.setStringAsync(proposal);
      Alert.alert('Copied!', 'Cover letter copied to clipboard. You can now paste it into your application.');
    } catch (error) {
      console.error('Failed to copy:', error);
      Alert.alert('Error', 'Failed to copy to clipboard.');
    }
  };

  const handleMarkApplied = async () => {
    if (!job) return;
    try {
      let matchId = existingMatch?.id;

      // Create match if it doesn't exist
      if (!matchId) {
        const match = await matchesApi.create(job.id);
        matchId = match.id;
      }

      // Use the mutation hook to update status (invalidates cache)
      await updateStatusMutation.mutateAsync({ matchId, status: 'applied' });

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

  // Interview Prep handlers
  const handleStartInterviewPrep = () => {
    if (!job) return;
    setShowInterviewPrepModal(true);
    setExpandedQuestion(null);
    interviewPrep.run({ job_id: job.id });
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return '#10b981';
      case 'medium':
        return '#f59e0b';
      case 'hard':
        return '#dc2626';
      default:
        return '#6b7280';
    }
  };

  // Salary Research handlers
  const handleStartSalaryResearch = () => {
    if (!job) return;
    setShowSalaryModal(true);
    salaryResearch.run({
      job_title: job.title,
      location: job.location,
      remote: job.remote,
    });
  };

  const formatSalary = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Skill Gap handlers
  const handleStartSkillGap = () => {
    if (!job) return;
    setShowSkillGapModal(true);
    skillGap.run({
      target_job_title: job.title,
      target_job_description: job.description,
    });
  };

  // Network Intelligence handlers
  const handleStartNetworkIntel = () => {
    if (!job) return;
    setShowNetworkModal(true);
    networkIntel.run({
      target_company: job.company,
      target_role: job.title,
    });
  };

  // Auto-Apply handlers
  const handleStartAutoApply = () => {
    if (!job) return;
    setShowAutoApplyModal(true);
    autoApply.run({
      job_title: job.title,
      company_name: job.company,
      job_description: job.description,
      job_url: job.url,
    });
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
            {/* Why This Matches - personalized explanation */}
            {scoredJob.explanation && (
              <View style={styles.explanationBox}>
                <View style={styles.explanationHeader}>
                  <Ionicons name="sparkles" size={16} color="#8b5cf6" />
                  <Text variant="labelMedium" style={styles.explanationTitle}>
                    Why This Matches You
                  </Text>
                </View>
                <Text variant="bodySmall" style={styles.explanationText}>
                  {scoredJob.explanation}
                </Text>
              </View>
            )}
          </Surface>
        )}

        {/* Client Risk Assessment */}
        <View style={styles.section}>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Client Risk Assessment
          </Text>
          <ClientRiskCard jobId={id} compact={false} />
        </View>

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
              {job.skills.map((skill: string, index: number) => (
                <Chip key={index} style={styles.skillChip}>
                  {skill}
                </Chip>
              ))}
            </View>
          </Surface>
        )}

        {/* Salary Research Section */}
        <Surface style={styles.salaryResearchSection}>
          <View style={styles.salaryResearchHeader}>
            <Ionicons name="cash" size={24} color="#10b981" />
            <View style={styles.salaryResearchHeaderText}>
              <View style={styles.agentTitleRow}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  Salary Insights
                </Text>
                <Chip compact style={styles.aiBadge} textStyle={styles.aiBadgeText}>✨ AI</Chip>
              </View>
              <Text variant="bodySmall" style={styles.salaryResearchSubtitle}>
                Research market rates and negotiation tips
              </Text>
            </View>
          </View>
          <Button
            mode="contained"
            onPress={handleStartSalaryResearch}
            disabled={salaryResearch.isRunning}
            icon="chart-line"
            style={styles.salaryResearchButton}
          >
            {salaryResearch.isRunning ? 'Researching...' : 'Research Salary'}
          </Button>
        </Surface>

        {/* Skill Gap Analysis Section */}
        <Surface style={styles.skillGapSection}>
          <View style={styles.skillGapHeader}>
            <Ionicons name="analytics" size={24} color="#8b5cf6" />
            <View style={styles.skillGapHeaderText}>
              <View style={styles.agentTitleRow}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  Skill Gap Analysis
                </Text>
                <Chip compact style={styles.aiBadge} textStyle={styles.aiBadgeText}>✨ AI</Chip>
              </View>
              <Text variant="bodySmall" style={styles.skillGapSubtitle}>
                See how your skills match this role
              </Text>
            </View>
          </View>
          <Button
            mode="contained"
            onPress={handleStartSkillGap}
            disabled={skillGap.isRunning}
            icon="school"
            style={styles.skillGapButton}
          >
            {skillGap.isRunning ? 'Analyzing...' : 'Analyze Skills'}
          </Button>
        </Surface>

        {/* Network Intelligence Section */}
        <Surface style={styles.networkIntelSection}>
          <View style={styles.networkIntelHeader}>
            <Ionicons name="people" size={24} color="#0ea5e9" />
            <View style={styles.networkIntelHeaderText}>
              <View style={styles.agentTitleRow}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  Company Intelligence
                </Text>
                <Chip compact style={styles.aiBadge} textStyle={styles.aiBadgeText}>✨ AI</Chip>
              </View>
              <Text variant="bodySmall" style={styles.networkIntelSubtitle}>
                Research {job.company} and find connections
              </Text>
            </View>
          </View>
          <Button
            mode="contained"
            onPress={handleStartNetworkIntel}
            disabled={networkIntel.isRunning}
            icon="domain"
            style={styles.networkIntelButton}
          >
            {networkIntel.isRunning ? 'Researching...' : 'Research Company'}
          </Button>
        </Surface>

        {/* Auto-Apply Section - Prepare application materials */}
        <Surface style={styles.autoApplySection}>
          <View style={styles.autoApplyHeader}>
            <Ionicons name="rocket" size={24} color="#8b5cf6" />
            <View style={styles.autoApplyHeaderText}>
              <View style={styles.agentTitleRow}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  Auto-Apply Preparation
                </Text>
                <Chip compact style={styles.aiBadge} textStyle={styles.aiBadgeText}>✨ AI</Chip>
              </View>
              <Text variant="bodySmall" style={styles.autoApplySubtitle}>
                Get fit assessment and prepared application materials
              </Text>
            </View>
          </View>
          <Button
            mode="contained"
            onPress={handleStartAutoApply}
            disabled={autoApply.isRunning}
            icon="flash"
            style={styles.autoApplyButton}
          >
            {autoApply.isRunning ? 'Preparing...' : 'Prepare Application'}
          </Button>
        </Surface>

        {/* Interview Prep Section - only for jobs in interviewing status */}
        {existingMatch?.status === 'interviewing' && (
          <Surface style={styles.interviewPrepSection}>
            <View style={styles.interviewPrepHeader}>
              <Ionicons name="school" size={24} color="#3b82f6" />
              <View style={styles.interviewPrepHeaderText}>
                <View style={styles.agentTitleRow}>
                  <Text variant="titleMedium" style={styles.sectionTitle}>
                    Interview Preparation
                  </Text>
                  <Chip compact style={styles.aiBadge} textStyle={styles.aiBadgeText}>✨ AI</Chip>
                </View>
                <Text variant="bodySmall" style={styles.interviewPrepSubtitle}>
                  Get AI-powered interview questions and tips
                </Text>
              </View>
            </View>
            <Button
              mode="contained"
              onPress={handleStartInterviewPrep}
              disabled={interviewPrep.isRunning}
              icon="briefcase-check"
              style={styles.interviewPrepButton}
            >
              {interviewPrep.isRunning ? 'Preparing...' : 'Start Interview Prep'}
            </Button>
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
              {/* Header with close button */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderText}>
                  <Text variant="titleLarge" style={styles.modalTitle}>
                    Generate Proposal
                  </Text>
                  <Text variant="bodyMedium" style={styles.modalSubtitle}>
                    Generate a custom proposal for this job using AI
                  </Text>
                </View>
                <Pressable
                  onPress={() => setShowProposalModal(false)}
                  style={styles.closeIconButton}
                >
                  <Ionicons name="close" size={24} color="#6b7280" />
                </Pressable>
              </View>

              {/* Mode Toggle */}
              {!proposal && (
                <View style={styles.modeToggleContainer}>
                  <Pressable
                    style={[styles.modeToggle, proposalMode === 'single' && styles.modeToggleActive]}
                    onPress={() => setProposalMode('single')}
                  >
                    <Ionicons name="document-text-outline" size={18} color={proposalMode === 'single' ? '#3b82f6' : '#6b7280'} />
                    <Text style={[styles.modeToggleText, proposalMode === 'single' && styles.modeToggleTextActive]}>Single</Text>
                  </Pressable>
                  <Pressable
                    style={[styles.modeToggle, proposalMode === 'ab' && styles.modeToggleActive]}
                    onPress={() => setProposalMode('ab')}
                  >
                    <Ionicons name="git-compare-outline" size={18} color={proposalMode === 'ab' ? '#3b82f6' : '#6b7280'} />
                    <Text style={[styles.modeToggleText, proposalMode === 'ab' && styles.modeToggleTextActive]}>A/B Test</Text>
                  </Pressable>
                </View>
              )}

              {/* A/B Test Mode */}
              {proposalMode === 'ab' && !proposal && existingMatch && (
                <ProposalABTest
                  jobMatchId={existingMatch.id}
                  onClose={() => {
                    setShowProposalModal(false);
                    setProposalMode('single');
                  }}
                  onMarkApplied={async (selectedVariant) => {
                    if (!job || !existingMatch) return;
                    try {
                      await updateStatusMutation.mutateAsync({ matchId: existingMatch.id, status: 'applied' });
                      setShowProposalModal(false);
                      setProposalMode('single');
                      Alert.alert('Success', 'Job marked as applied with your selected proposal!');
                      router.back();
                    } catch (err) {
                      console.error('Failed to mark as applied:', err);
                      Alert.alert('Error', 'Failed to mark as applied. Please try again.');
                    }
                  }}
                />
              )}

              {/* Need to save job first for A/B mode */}
              {proposalMode === 'ab' && !proposal && !existingMatch && (
                <View style={styles.saveFirstContainer}>
                  <Ionicons name="bookmark-outline" size={48} color="#6b7280" />
                  <Text variant="bodyMedium" style={styles.saveFirstText}>
                    Save this job first to use A/B testing
                  </Text>
                  <Button
                    mode="contained"
                    onPress={handleSave}
                    loading={saveJobMutation.isPending}
                    icon="bookmark"
                  >
                    Save Job
                  </Button>
                </View>
              )}

              {/* Single Mode - existing proposal display */}
              {proposalMode === 'single' && proposal && (
                <View style={styles.proposalContent}>
                  {/* Key Points if available */}
                  {keyPoints.length > 0 && (
                    <View style={styles.keyPointsContainer}>
                      <Text variant="labelMedium" style={styles.keyPointsLabel}>
                        Key Points Highlighted:
                      </Text>
                      <View style={styles.keyPointsChips}>
                        {keyPoints.map((point, idx) => (
                          <Chip key={idx} style={styles.keyPointChip} textStyle={styles.keyPointChipText}>
                            {point}
                          </Chip>
                        ))}
                      </View>
                    </View>
                  )}
                  <ScrollView style={styles.proposalScroll} nestedScrollEnabled>
                    <TextInput
                      value={proposal}
                      onChangeText={setProposal}
                      multiline
                      numberOfLines={12}
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
                      contentStyle={styles.modalButtonContent}
                    >
                      Copy
                    </Button>
                    <Button
                      mode="contained"
                      onPress={handleMarkApplied}
                      icon="check"
                      style={[styles.modalButton, styles.primaryButton]}
                      contentStyle={styles.modalButtonContent}
                    >
                      Mark Applied
                    </Button>
                  </View>
                </View>
              )}

              {/* Single Mode - generate container */}
              {proposalMode === 'single' && !proposal && (
                <View style={styles.generateContainer}>
                  {/* Style Selection */}
                  <View style={styles.toneSelector}>
                    <Text variant="labelMedium" style={styles.toneSelectorLabel}>
                      Style
                    </Text>
                    <Menu
                      visible={styleMenuVisible}
                      onDismiss={() => setStyleMenuVisible(false)}
                      anchor={
                        <Button
                          mode="outlined"
                          onPress={() => setStyleMenuVisible(true)}
                          icon="chevron-down"
                          contentStyle={styles.styleDropdownContent}
                          style={styles.styleDropdown}
                        >
                          {coverLetterStyle.charAt(0).toUpperCase() + coverLetterStyle.slice(1)}
                        </Button>
                      }
                    >
                      <Menu.Item
                        onPress={() => { setCoverLetterStyle('modern'); setStyleMenuVisible(false); }}
                        title="Modern"
                        leadingIcon={coverLetterStyle === 'modern' ? 'check' : undefined}
                      />
                      <Menu.Item
                        onPress={() => { setCoverLetterStyle('traditional'); setStyleMenuVisible(false); }}
                        title="Traditional"
                        leadingIcon={coverLetterStyle === 'traditional' ? 'check' : undefined}
                      />
                      <Menu.Item
                        onPress={() => { setCoverLetterStyle('creative'); setStyleMenuVisible(false); }}
                        title="Creative"
                        leadingIcon={coverLetterStyle === 'creative' ? 'check' : undefined}
                      />
                      <Menu.Item
                        onPress={() => { setCoverLetterStyle('executive'); setStyleMenuVisible(false); }}
                        title="Executive"
                        leadingIcon={coverLetterStyle === 'executive' ? 'check' : undefined}
                      />
                    </Menu>
                  </View>

                  {/* Progress/Status */}
                  {(coverLetter.isRunning || (coverLetter.isCompleted && !coverLetter.result)) && (
                    <View style={styles.progressContainer}>
                      <View style={styles.progressHeader}>
                        <ActivityIndicator size="small" color="#3b82f6" />
                        <Text variant="bodySmall" style={styles.progressStep}>
                          {coverLetter.isCompleted ? 'Loading results...' : (coverLetter.currentStep || 'Generating cover letter...')}
                        </Text>
                      </View>
                      <ProgressBar
                        progress={coverLetter.isCompleted ? 1 : coverLetter.progress / 100}
                        color="#3b82f6"
                        style={styles.progressBar}
                      />
                    </View>
                  )}

                  {/* Error state */}
                  {coverLetter.isFailed && (
                    <View style={styles.errorBanner}>
                      <Text variant="bodySmall" style={styles.errorBannerText}>
                        {coverLetter.errors[0] || 'Generation failed. Please try again.'}
                      </Text>
                      <Button
                        mode="text"
                        onPress={() => coverLetter.reset()}
                        compact
                        labelStyle={styles.dismissLabel}
                      >
                        Dismiss
                      </Button>
                    </View>
                  )}

                  <Button
                    mode="contained"
                    onPress={handleGenerateProposal}
                    loading={coverLetter.isRunning}
                    disabled={coverLetter.isRunning}
                    icon="auto-fix"
                    contentStyle={styles.generateButtonContent}
                  >
                    {coverLetter.isRunning ? 'Generating...' : 'Generate Cover Letter'}
                  </Button>
                  <Button
                    mode="text"
                    onPress={() => setShowProposalModal(false)}
                    style={styles.cancelButton}
                  >
                    Cancel
                  </Button>
                </View>
              )}
            </Surface>
          </KeyboardAvoidingView>
        </View>
      )}

      {/* Interview Prep Modal */}
      {showInterviewPrepModal && (
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => setShowInterviewPrepModal(false)}
          />
          <View style={styles.modalKeyboardView}>
            <Surface style={styles.interviewPrepModal}>
              {/* Header */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderText}>
                  <Text variant="titleLarge" style={styles.modalTitle}>
                    Interview Prep
                  </Text>
                  <Text variant="bodySmall" style={styles.modalSubtitle}>
                    {job?.company} - {job?.title}
                  </Text>
                </View>
                <Pressable
                  onPress={() => {
                    setShowInterviewPrepModal(false);
                    interviewPrep.reset();
                  }}
                  style={styles.closeIconButton}
                >
                  <Ionicons name="close" size={24} color="#6b7280" />
                </Pressable>
              </View>

              {/* Loading State */}
              {(interviewPrep.isRunning || (interviewPrep.isCompleted && !interviewPrep.result)) && (
                <AgentLoadingState
                  color="#3b82f6"
                  progress={interviewPrep.isCompleted ? 1 : interviewPrep.progress / 100}
                  statusText={interviewPrep.isCompleted ? 'Loading results...' : (interviewPrep.currentStep || 'Preparing interview materials...')}
                />
              )}

              {/* Error State */}
              {interviewPrep.isFailed && (
                <View style={styles.interviewPrepError}>
                  <Ionicons name="warning" size={48} color="#dc2626" />
                  <Text variant="bodyMedium" style={styles.interviewPrepErrorText}>
                    {interviewPrep.errors[0] || 'Failed to prepare interview materials'}
                  </Text>
                  <Button mode="contained" onPress={handleStartInterviewPrep}>
                    Try Again
                  </Button>
                </View>
              )}

              {/* Results */}
              {interviewPrep.isCompleted && interviewPrep.result && (
                <ScrollView style={styles.interviewPrepContent}>
                  {/* Focus Areas */}
                  {interviewPrep.result.focus_areas?.length > 0 && (
                    <View style={styles.interviewPrepSection2}>
                      <Text variant="titleSmall" style={styles.interviewPrepSectionTitle}>
                        Focus Areas
                      </Text>
                      <View style={styles.focusAreasContainer}>
                        {interviewPrep.result.focus_areas.map((area: string, idx: number) => (
                          <Chip key={idx} style={styles.focusAreaChip}>
                            {area}
                          </Chip>
                        ))}
                      </View>
                    </View>
                  )}

                  {/* Prep Tips */}
                  {interviewPrep.result.prep_tips?.length > 0 && (
                    <View style={styles.interviewPrepSection2}>
                      <Text variant="titleSmall" style={styles.interviewPrepSectionTitle}>
                        Preparation Tips
                      </Text>
                      {interviewPrep.result.prep_tips.map((tip: string, idx: number) => (
                        <View key={idx} style={styles.prepTipItem}>
                          <Ionicons name="checkmark-circle" size={18} color="#10b981" />
                          <Text variant="bodyMedium" style={styles.prepTipText}>
                            {tip}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Interview Questions */}
                  {interviewPrep.result.questions?.length > 0 && (
                    <View style={styles.interviewPrepSection2}>
                      <Text variant="titleSmall" style={styles.interviewPrepSectionTitle}>
                        Practice Questions ({interviewPrep.result.questions?.length || 0})
                      </Text>
                      {interviewPrep.result.questions.map((question: InterviewQuestion, idx: number) => (
                        <Pressable
                          key={idx}
                          onPress={() => setExpandedQuestion(expandedQuestion === idx ? null : idx)}
                        >
                          <Surface style={styles.questionCard}>
                            <View style={styles.questionHeader}>
                              <View style={styles.questionMeta}>
                                <Chip
                                  style={[
                                    styles.difficultyChip,
                                    { backgroundColor: getDifficultyColor(question.difficulty) + '20' },
                                  ]}
                                  textStyle={{ color: getDifficultyColor(question.difficulty), fontSize: 10 }}
                                >
                                  {question.difficulty}
                                </Chip>
                                <Chip style={styles.typeChip} textStyle={styles.typeChipText}>
                                  {question.type}
                                </Chip>
                              </View>
                              <Ionicons
                                name={expandedQuestion === idx ? 'chevron-up' : 'chevron-down'}
                                size={20}
                                color="#6b7280"
                              />
                            </View>
                            <Text variant="bodyMedium" style={styles.questionText}>
                              {question.question}
                            </Text>
                            {expandedQuestion === idx && (
                              <View style={styles.questionExpanded}>
                                <Divider style={styles.questionDivider} />
                                {question.tips.length > 0 && (
                                  <View style={styles.questionTips}>
                                    <Text variant="labelMedium" style={styles.questionTipsLabel}>
                                      Tips:
                                    </Text>
                                    {question.tips.map((tip: string, tipIdx: number) => (
                                      <Text key={tipIdx} variant="bodySmall" style={styles.questionTip}>
                                        • {tip}
                                      </Text>
                                    ))}
                                  </View>
                                )}
                                {question.sample_answer && (
                                  <View style={styles.sampleAnswer}>
                                    <Text variant="labelMedium" style={styles.sampleAnswerLabel}>
                                      Sample Answer:
                                    </Text>
                                    <Text variant="bodySmall" style={styles.sampleAnswerText}>
                                      {question.sample_answer}
                                    </Text>
                                  </View>
                                )}
                              </View>
                            )}
                          </Surface>
                        </Pressable>
                      ))}
                    </View>
                  )}
                </ScrollView>
              )}
            </Surface>
          </View>
        </View>
      )}

      {/* Salary Research Modal */}
      {showSalaryModal && (
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => setShowSalaryModal(false)}
          />
          <View style={styles.modalKeyboardView}>
            <Surface style={styles.salaryModal}>
              {/* Header */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderText}>
                  <Text variant="titleLarge" style={styles.modalTitle}>
                    Salary Research
                  </Text>
                  <Text variant="bodySmall" style={styles.modalSubtitle}>
                    {job?.title}
                  </Text>
                </View>
                <Pressable
                  onPress={() => {
                    setShowSalaryModal(false);
                    salaryResearch.reset();
                  }}
                  style={styles.closeIconButton}
                >
                  <Ionicons name="close" size={24} color="#6b7280" />
                </Pressable>
              </View>

              {/* Loading State */}
              {(salaryResearch.isRunning || (salaryResearch.isCompleted && !salaryResearch.result)) && (
                <AgentLoadingState
                  color="#10b981"
                  progress={salaryResearch.isCompleted ? 1 : salaryResearch.progress / 100}
                  statusText={salaryResearch.isCompleted ? 'Loading results...' : (salaryResearch.currentStep || 'Researching market rates...')}
                />
              )}

              {/* Error State */}
              {salaryResearch.isFailed && (
                <View style={styles.salaryError}>
                  <Ionicons name="warning" size={48} color="#dc2626" />
                  <Text variant="bodyMedium" style={styles.salaryErrorText}>
                    {salaryResearch.errors[0] || 'Failed to research salary data'}
                  </Text>
                  <Button mode="contained" onPress={handleStartSalaryResearch}>
                    Try Again
                  </Button>
                </View>
              )}

              {/* Results */}
              {salaryResearch.isCompleted && salaryResearch.result?.result && (
                <ScrollView style={styles.salaryContent}>
                  {/* Market Rate */}
                  {salaryResearch.result.result.salary_range && (
                    <View style={styles.salarySection}>
                      <Text variant="titleSmall" style={styles.salarySectionTitle}>
                        Market Rate
                      </Text>
                      <View style={styles.salaryRangeCard}>
                        <View style={styles.salaryRangeHeader}>
                          <Text variant="labelSmall" style={styles.salaryRangeLabel}>
                            Low
                          </Text>
                          <Text variant="labelSmall" style={styles.salaryRangeLabel}>
                            Median
                          </Text>
                          <Text variant="labelSmall" style={styles.salaryRangeLabel}>
                            High
                          </Text>
                        </View>
                        <View style={styles.salaryRangeValues}>
                          <Text variant="bodyLarge" style={styles.salaryValueLow}>
                            {formatSalary(salaryResearch.result.result.salary_range.min_salary, salaryResearch.result.result.salary_range.currency)}
                          </Text>
                          <Text variant="headlineSmall" style={styles.salaryValueMedian}>
                            {formatSalary(salaryResearch.result.result.salary_range.median_salary, salaryResearch.result.result.salary_range.currency)}
                          </Text>
                          <Text variant="bodyLarge" style={styles.salaryValueHigh}>
                            {formatSalary(salaryResearch.result.result.salary_range.max_salary, salaryResearch.result.result.salary_range.currency)}
                          </Text>
                        </View>
                        <View style={styles.salaryBar}>
                          <View style={styles.salaryBarFill} />
                          <View style={styles.salaryBarMarker} />
                        </View>
                      </View>
                    </View>
                  )}

                  {/* Total Compensation */}
                  {salaryResearch.result.result.total_comp_estimate > 0 && (
                    <View style={styles.salarySection}>
                      <Text variant="titleSmall" style={styles.salarySectionTitle}>
                        Total Compensation Estimate
                      </Text>
                      <View style={styles.totalCompCard}>
                        <Text variant="headlineMedium" style={styles.totalCompValue}>
                          {formatSalary(salaryResearch.result.result.total_comp_estimate, salaryResearch.result.result.salary_range?.currency || 'USD')}
                        </Text>
                        {salaryResearch.result.result.location_adjustment !== 0 && (
                          <Text variant="bodySmall" style={styles.adjustmentText}>
                            Location adjustment: {salaryResearch.result.result.location_adjustment > 0 ? '+' : ''}{salaryResearch.result.result.location_adjustment}%
                          </Text>
                        )}
                        {salaryResearch.result.result.experience_adjustment !== 0 && (
                          <Text variant="bodySmall" style={styles.adjustmentText}>
                            Experience adjustment: {salaryResearch.result.result.experience_adjustment > 0 ? '+' : ''}{salaryResearch.result.result.experience_adjustment}%
                          </Text>
                        )}
                      </View>
                    </View>
                  )}

                  {/* Key Factors */}
                  {salaryResearch.result.result.market_data?.key_factors && salaryResearch.result.result.market_data.key_factors.length > 0 && (
                    <View style={styles.salarySection}>
                      <Text variant="titleSmall" style={styles.salarySectionTitle}>
                        Key Factors
                      </Text>
                      {salaryResearch.result.result.market_data.key_factors.map((factor: string, idx: number) => (
                        <View key={idx} style={styles.factorItem}>
                          <Ionicons name="trending-up" size={16} color="#10b981" />
                          <Text variant="bodyMedium" style={styles.factorText}>
                            {factor}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Negotiation Leverage */}
                  {salaryResearch.result.result.negotiation_leverage && salaryResearch.result.result.negotiation_leverage.length > 0 && (
                    <View style={styles.salarySection}>
                      <Text variant="titleSmall" style={styles.salarySectionTitle}>
                        Negotiation Leverage
                      </Text>
                      {salaryResearch.result.result.negotiation_leverage.map((point: string, idx: number) => (
                        <View key={idx} style={styles.negotiationTipItem}>
                          <Ionicons name="bulb" size={18} color="#f59e0b" />
                          <Text variant="bodyMedium" style={styles.negotiationTipText}>
                            {point}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Negotiation Scripts */}
                  {salaryResearch.result.result.negotiation_scripts && salaryResearch.result.result.negotiation_scripts.length > 0 && (
                    <View style={styles.salarySection}>
                      <Text variant="titleSmall" style={styles.salarySectionTitle}>
                        Negotiation Scripts
                      </Text>
                      {salaryResearch.result.result.negotiation_scripts.map((script: any, idx: number) => (
                        <View key={idx} style={styles.scriptCard}>
                          <Text variant="labelMedium" style={styles.scriptScenario}>
                            {script.scenario}
                          </Text>
                          <Text variant="bodySmall" style={styles.scriptText}>
                            {script.opening}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                </ScrollView>
              )}
            </Surface>
          </View>
        </View>
      )}

      {/* Skill Gap Modal */}
      {showSkillGapModal && (
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => {
              setShowSkillGapModal(false);
              skillGap.reset();
            }}
          />
          <View style={styles.modalKeyboardView}>
            <Surface style={styles.skillGapModal}>
              {/* Modal Header */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderText}>
                  <Text variant="titleLarge" style={styles.modalTitle}>
                    Skill Gap Analysis
                  </Text>
                  <Text variant="bodySmall" style={styles.modalSubtitle}>
                    {job?.title} at {job?.company}
                  </Text>
                </View>
                <Pressable
                  onPress={() => {
                    setShowSkillGapModal(false);
                    skillGap.reset();
                  }}
                  style={styles.closeIconButton}
                >
                  <Ionicons name="close" size={24} color="#6b7280" />
                </Pressable>
              </View>

              {/* Loading State */}
              {(skillGap.isRunning || (skillGap.isCompleted && !skillGap.result)) && (
                <AgentLoadingState
                  color="#8b5cf6"
                  progress={skillGap.isCompleted ? 1 : skillGap.progress / 100}
                  statusText={skillGap.isCompleted ? 'Loading results...' : (skillGap.currentStep || 'Analyzing your skills...')}
                />
              )}

              {/* Error State */}
              {skillGap.isFailed && (
                <View style={styles.skillGapError}>
                  <Ionicons name="alert-circle" size={48} color="#dc2626" />
                  <Text variant="bodyMedium" style={styles.skillGapErrorText}>
                    {skillGap.errors[0] || 'Failed to analyze skills'}
                  </Text>
                  <Button mode="contained" onPress={handleStartSkillGap}>
                    Try Again
                  </Button>
                </View>
              )}

              {/* Results State */}
              {skillGap.isCompleted && skillGap.result && (
                <ScrollView style={styles.skillGapContent}>
                  {/* Match Score - backend uses result.skill_overlap_percent */}
                  {skillGap.result.result?.skill_overlap_percent !== undefined && (
                    <View style={styles.skillGapScoreSection}>
                      <View style={styles.skillGapScoreCircle}>
                        <Text variant="headlineLarge" style={styles.skillGapScoreValue}>
                          {Math.round(skillGap.result.result.skill_overlap_percent)}%
                        </Text>
                        <Text variant="bodySmall" style={styles.skillGapScoreLabel}>
                          Match
                        </Text>
                      </View>
                    </View>
                  )}

                  {/* Matched Skills - backend uses result.transferable_skills */}
                  {(skillGap.result.result?.transferable_skills?.length > 0 || skillGap.result.result?.current_skills?.length > 0) && (
                    <View style={styles.skillGapResultSection}>
                      <Text variant="titleMedium" style={styles.skillGapSectionTitle}>
                        <Ionicons name="checkmark-circle" size={20} color="#22c55e" /> Skills You Have
                      </Text>
                      <View style={styles.skillGapChipsContainer}>
                        {[...(skillGap.result.result?.transferable_skills || []), ...(skillGap.result.result?.current_skills || [])].filter((skill, idx, arr) => arr.indexOf(skill) === idx).map((skill: string, idx: number) => (
                          <Chip key={idx} style={styles.matchedSkillChip}>
                            {skill}
                          </Chip>
                        ))}
                      </View>
                    </View>
                  )}

                  {/* Missing Skills - backend uses result.skill_gaps */}
                  {skillGap.result.result?.skill_gaps?.length > 0 && (
                    <View style={styles.skillGapResultSection}>
                      <Text variant="titleMedium" style={styles.skillGapSectionTitle}>
                        <Ionicons name="school" size={20} color="#f59e0b" /> Skills to Develop
                      </Text>
                      {skillGap.result.result.skill_gaps.map((item: any, idx: number) => (
                        <View key={idx} style={styles.missingSkillItem}>
                          <View style={styles.missingSkillHeader}>
                            <Text variant="bodyLarge" style={styles.missingSkillName}>
                              {item.skill}
                            </Text>
                            <Chip
                              style={[
                                styles.importanceChip,
                                item.priority === 'high'
                                  ? styles.requiredChip
                                  : styles.preferredChip,
                              ]}
                              textStyle={styles.importanceChipText}
                            >
                              {item.priority === 'high' ? 'required' : item.priority}
                            </Chip>
                          </View>
                          {item.gap_level && (
                            <Text variant="bodySmall" style={styles.currentLevelText}>
                              Gap level: {item.gap_level.replace(/_/g, ' ')}
                            </Text>
                          )}
                          {item.learning_effort && (
                            <Text variant="bodySmall" style={styles.currentLevelText}>
                              Learning effort: {item.learning_effort}
                            </Text>
                          )}
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Quick Wins */}
                  {skillGap.result.result?.quick_wins?.length > 0 && (
                    <View style={styles.skillGapResultSection}>
                      <Text variant="titleMedium" style={styles.skillGapSectionTitle}>
                        <Ionicons name="flash" size={20} color="#22c55e" /> Quick Wins
                      </Text>
                      {skillGap.result.result.quick_wins.map((rec: string, idx: number) => (
                        <View key={idx} style={styles.recommendationItem}>
                          <Ionicons name="checkmark" size={16} color="#22c55e" />
                          <Text variant="bodyMedium" style={styles.recommendationText}>
                            {rec}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Long-term Investments */}
                  {skillGap.result.result?.long_term_investments?.length > 0 && (
                    <View style={styles.skillGapResultSection}>
                      <Text variant="titleMedium" style={styles.skillGapSectionTitle}>
                        <Ionicons name="bulb" size={20} color="#3b82f6" /> Long-term Investments
                      </Text>
                      {skillGap.result.result.long_term_investments.map((rec: string, idx: number) => (
                        <View key={idx} style={styles.recommendationItem}>
                          <Ionicons name="arrow-forward" size={16} color="#3b82f6" />
                          <Text variant="bodyMedium" style={styles.recommendationText}>
                            {rec}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Recommended Certifications */}
                  {skillGap.result.result?.recommended_certifications?.length > 0 && (
                    <View style={styles.skillGapResultSection}>
                      <Text variant="titleMedium" style={styles.skillGapSectionTitle}>
                        <Ionicons name="ribbon" size={20} color="#8b5cf6" /> Recommended Certifications
                      </Text>
                      {skillGap.result.result.recommended_certifications.map((cert: any, idx: number) => (
                        <View key={idx} style={styles.recommendationItem}>
                          <Ionicons name="school" size={16} color="#8b5cf6" />
                          <Text variant="bodyMedium" style={styles.recommendationText}>
                            {cert.name || cert}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}
                </ScrollView>
              )}
            </Surface>
          </View>
        </View>
      )}

      {/* Network Intelligence Modal */}
      {showNetworkModal && (
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => {
              setShowNetworkModal(false);
              networkIntel.reset();
            }}
          />
          <View style={styles.modalKeyboardView}>
            <Surface style={styles.networkModal}>
              {/* Modal Header */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderText}>
                  <Text variant="titleLarge" style={styles.modalTitle}>
                    Company Intelligence
                  </Text>
                  <Text variant="bodySmall" style={styles.modalSubtitle}>
                    {job?.company}
                  </Text>
                </View>
                <Pressable
                  onPress={() => {
                    setShowNetworkModal(false);
                    networkIntel.reset();
                  }}
                  style={styles.closeIconButton}
                >
                  <Ionicons name="close" size={24} color="#6b7280" />
                </Pressable>
              </View>

              {/* Loading State */}
              {(networkIntel.isRunning || (networkIntel.isCompleted && !networkIntel.result)) && (
                <AgentLoadingState
                  color="#0ea5e9"
                  progress={networkIntel.isCompleted ? 1 : networkIntel.progress / 100}
                  statusText={networkIntel.isCompleted ? 'Loading results...' : (networkIntel.currentStep || 'Researching company...')}
                />
              )}

              {/* Error State */}
              {networkIntel.isFailed && (
                <View style={styles.networkError}>
                  <Ionicons name="alert-circle" size={48} color="#dc2626" />
                  <Text variant="bodyMedium" style={styles.networkErrorText}>
                    {networkIntel.errors[0] || 'Failed to research company'}
                  </Text>
                  <Button mode="contained" onPress={handleStartNetworkIntel}>
                    Try Again
                  </Button>
                </View>
              )}

              {/* Results State */}
              {networkIntel.isCompleted && networkIntel.result?.result && (
                <ScrollView style={styles.networkContent}>
                  {/* Company Culture */}
                  {networkIntel.result.result.company_culture?.values?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="heart" size={18} color="#ec4899" /> Company Culture
                      </Text>
                      {networkIntel.result.result.company_culture.values.map((item: string, idx: number) => (
                        <View key={idx} style={styles.networkInsightItem}>
                          <Ionicons name="checkmark" size={16} color="#ec4899" />
                          <Text variant="bodyMedium" style={styles.networkInsightText}>
                            {item}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Recent News */}
                  {networkIntel.result.result.company_info?.recent_news?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="newspaper" size={18} color="#8b5cf6" /> Recent News
                      </Text>
                      {networkIntel.result.result.company_info.recent_news.map((item: string, idx: number) => (
                        <View key={idx} style={styles.networkNewsItem}>
                          <Ionicons name="document-text" size={16} color="#8b5cf6" />
                          <Text variant="bodyMedium" style={styles.networkNewsText}>
                            {item}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Hiring Trends */}
                  {networkIntel.result.result.hiring_trends?.growth_areas?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="trending-up" size={18} color="#10b981" /> Hiring Trends
                      </Text>
                      {networkIntel.result.result.hiring_trends.growth_areas.map((item: string, idx: number) => (
                        <View key={idx} style={styles.networkTrendItem}>
                          <Ionicons name="arrow-forward" size={16} color="#10b981" />
                          <Text variant="bodyMedium" style={styles.networkTrendText}>
                            {item}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Hot Skills */}
                  {networkIntel.result.result.hiring_trends?.hot_skills?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="star" size={18} color="#f59e0b" /> In-Demand Skills
                      </Text>
                      <View style={styles.chipContainer}>
                        {networkIntel.result.result.hiring_trends.hot_skills.map((skill: string, idx: number) => (
                          <Chip key={idx} style={styles.skillChip}>{skill}</Chip>
                        ))}
                      </View>
                    </View>
                  )}

                  {/* Potential Contacts */}
                  {networkIntel.result.result.potential_contacts?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="people" size={18} color="#0ea5e9" /> Potential Contacts
                      </Text>
                      {networkIntel.result.result.potential_contacts.map((contact: any, idx: number) => (
                        <View key={idx} style={styles.connectionItem}>
                          <View style={styles.connectionAvatar}>
                            <Ionicons name="person" size={20} color="#0ea5e9" />
                          </View>
                          <View style={styles.connectionDetails}>
                            <Text variant="bodyMedium" style={styles.connectionText}>
                              {contact.role_type} - {contact.department}
                            </Text>
                            <Text variant="bodySmall" style={styles.connectionSubtext}>
                              {contact.value_proposition}
                            </Text>
                          </View>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Talking Points */}
                  {networkIntel.result.result.talking_points?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="chatbubble" size={18} color="#f59e0b" /> Talking Points
                      </Text>
                      {networkIntel.result.result.talking_points.map((point: string, idx: number) => (
                        <View key={idx} style={styles.outreachItem}>
                          <Ionicons name="bulb" size={16} color="#f59e0b" />
                          <Text variant="bodyMedium" style={styles.outreachText}>
                            {point}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Outreach Templates */}
                  {networkIntel.result.result.outreach_templates?.length > 0 && (
                    <View style={styles.networkResultSection}>
                      <Text variant="titleMedium" style={styles.networkSectionTitle}>
                        <Ionicons name="mail" size={18} color="#8b5cf6" /> Outreach Templates
                      </Text>
                      {networkIntel.result.result.outreach_templates.map((template: any, idx: number) => (
                        <Surface key={idx} style={styles.templateCard}>
                          <Text variant="titleSmall" style={styles.templateTitle}>
                            {template.scenario}
                          </Text>
                          <Text variant="bodySmall" style={styles.templatePlatform}>
                            Platform: {template.platform} | Tone: {template.tone}
                          </Text>
                          <Text variant="bodyMedium" style={styles.templateMessage}>
                            {template.message}
                          </Text>
                        </Surface>
                      ))}
                    </View>
                  )}
                </ScrollView>
              )}
            </Surface>
          </View>
        </View>
      )}

      {/* Auto-Apply Modal */}
      {showAutoApplyModal && (
        <View style={styles.modalOverlay}>
          <Pressable
            style={styles.modalBackdrop}
            onPress={() => {
              setShowAutoApplyModal(false);
              autoApply.reset();
            }}
          />
          <View style={styles.modalKeyboardView}>
            <Surface style={styles.autoApplyModal}>
              <View style={styles.autoApplyModalContent}>
              {/* Modal Header */}
              <View style={styles.modalHeader}>
                <View style={styles.modalHeaderText}>
                  <Text variant="titleLarge" style={styles.modalTitle}>
                    Auto-Apply Preparation
                  </Text>
                  <Text variant="bodySmall" style={styles.modalSubtitle}>
                    {job?.company} - {job?.title}
                  </Text>
                </View>
                <Pressable
                  onPress={() => {
                    setShowAutoApplyModal(false);
                    autoApply.reset();
                  }}
                  style={styles.closeIconButton}
                >
                  <Ionicons name="close" size={24} color="#6b7280" />
                </Pressable>
              </View>

              {/* Loading State */}
              {(autoApply.isRunning || (autoApply.isCompleted && !autoApply.result)) && (
                <AgentLoadingState
                  color="#8b5cf6"
                  progress={autoApply.isCompleted ? 1 : autoApply.progress / 100}
                  statusText={autoApply.isCompleted ? 'Loading results...' : (autoApply.currentStep || 'Preparing your application...')}
                />
              )}

              {/* Error State */}
              {autoApply.isFailed && (
                <View style={styles.autoApplyError}>
                  <Ionicons name="alert-circle" size={48} color="#dc2626" />
                  <Text variant="bodyMedium" style={styles.autoApplyErrorText}>
                    {autoApply.errors[0] || 'Failed to prepare application'}
                  </Text>
                  <Button mode="contained" onPress={handleStartAutoApply}>
                    Try Again
                  </Button>
                </View>
              )}

              {/* Results State */}
              {autoApply.isCompleted && autoApply.result?.result && (
                <ScrollView style={styles.autoApplyContent}>
                  {/* Fit Assessment */}
                  {autoApply.result.result.fit_assessment && (
                    <View style={styles.autoApplyResultSection}>
                      <Text variant="titleMedium" style={styles.autoApplySectionTitle}>
                        <Ionicons name="analytics" size={18} color="#8b5cf6" /> Fit Assessment
                      </Text>

                      {/* Overall Fit Score */}
                      <View style={styles.fitScoreContainer}>
                        <View style={styles.fitScoreCircle}>
                          <Text variant="headlineMedium" style={styles.fitScoreText}>
                            {autoApply.result.result.fit_assessment.overall_match_score}%
                          </Text>
                        </View>
                        <Text variant="bodyMedium" style={styles.fitScoreLabel}>
                          Overall Fit
                        </Text>
                      </View>

                      {/* Strengths */}
                      {autoApply.result.result.fit_assessment.strengths?.length > 0 && (
                        <View style={styles.fitSubsection}>
                          <Text variant="bodyLarge" style={styles.fitSubsectionTitle}>
                            <Ionicons name="checkmark-circle" size={16} color="#22c55e" /> Strengths
                          </Text>
                          {autoApply.result.result.fit_assessment.strengths.map((strength: string, idx: number) => (
                            <View key={idx} style={styles.strengthItem}>
                              <Ionicons name="add" size={16} color="#22c55e" />
                              <Text variant="bodyMedium" style={styles.strengthText}>
                                {strength}
                              </Text>
                            </View>
                          ))}
                        </View>
                      )}

                      {/* Gaps */}
                      {autoApply.result.result.fit_assessment.gaps?.length > 0 && (
                        <View style={styles.fitSubsection}>
                          <Text variant="bodyLarge" style={styles.fitSubsectionTitle}>
                            <Ionicons name="warning" size={16} color="#f59e0b" /> Areas to Address
                          </Text>
                          {autoApply.result.result.fit_assessment.gaps.map((gap: string, idx: number) => (
                            <View key={idx} style={styles.gapItem}>
                              <Ionicons name="alert" size={16} color="#f59e0b" />
                              <Text variant="bodyMedium" style={styles.gapText}>
                                {gap}
                              </Text>
                            </View>
                          ))}
                        </View>
                      )}
                    </View>
                  )}

                  {/* Prepared Materials */}
                  <View style={styles.autoApplyResultSection}>
                    <Text variant="titleMedium" style={styles.autoApplySectionTitle}>
                      <Ionicons name="document-text" size={18} color="#0ea5e9" /> Prepared Materials
                    </Text>

                    {/* Cover Letter Preview */}
                    {autoApply.result.result.cover_letter && (
                      <View style={styles.materialCard}>
                        <View style={styles.materialHeader}>
                          <Ionicons name="mail" size={20} color="#8b5cf6" />
                          <Text variant="bodyLarge" style={styles.materialTitle}>
                            Cover Letter
                          </Text>
                        </View>
                        <Text
                          variant="bodyMedium"
                          style={styles.materialPreview}
                          numberOfLines={4}
                        >
                          {autoApply.result.result.cover_letter}
                        </Text>
                      </View>
                    )}

                    {/* Resume Highlights */}
                    {autoApply.result.result.customized_resume_points?.length > 0 && (
                      <View style={styles.materialCard}>
                        <View style={styles.materialHeader}>
                          <Ionicons name="star" size={20} color="#f59e0b" />
                          <Text variant="bodyLarge" style={styles.materialTitle}>
                            Key Resume Highlights
                          </Text>
                        </View>
                        {autoApply.result.result.customized_resume_points.map((highlight: string, idx: number) => (
                          <View key={idx} style={styles.highlightItem}>
                            <Ionicons name="checkmark-circle" size={16} color="#f59e0b" />
                            <Text variant="bodyMedium" style={styles.highlightText}>
                              {highlight}
                            </Text>
                          </View>
                        ))}
                      </View>
                    )}

                    {/* Screening Questions */}
                    {autoApply.result.result.screening_questions?.length > 0 && (
                      <View style={styles.materialCard}>
                        <View style={styles.materialHeader}>
                          <Ionicons name="help-circle" size={20} color="#10b981" />
                          <Text variant="bodyLarge" style={styles.materialTitle}>
                            Screening Questions
                          </Text>
                        </View>
                        {autoApply.result.result.screening_questions.map((item: any, idx: number) => (
                          <View key={idx} style={styles.screeningItem}>
                            <Text variant="bodyMedium" style={styles.screeningQuestion}>
                              Q: {item.question}
                            </Text>
                            <Text variant="bodyMedium" style={styles.screeningAnswer}>
                              A: {item.answer}
                            </Text>
                          </View>
                        ))}
                      </View>
                    )}
                  </View>
                </ScrollView>
              )}
              </View>
            </Surface>
          </View>
        </View>
      )}

      {/* AI Agents FAB - hide when any modal is open */}
      {job && !showProposalModal && !showInterviewPrepModal && !showSalaryModal && !showSkillGapModal && !showNetworkModal && !showAutoApplyModal && (
        <FAB.Group
          open={fabOpen}
          visible
          icon={fabOpen ? 'close' : 'robot'}
            actions={[
              {
                icon: 'file-document-edit',
                label: 'Cover Letter',
                onPress: () => setShowProposalModal(true),
                color: '#6366f1',
              },
              {
                icon: 'chart-line',
                label: 'Salary Research',
                onPress: handleStartSalaryResearch,
                color: '#10b981',
              },
              {
                icon: 'school',
                label: 'Skill Gap',
                onPress: handleStartSkillGap,
                color: '#8b5cf6',
              },
              {
                icon: 'domain',
                label: 'Company Intel',
                onPress: handleStartNetworkIntel,
                color: '#0ea5e9',
              },
              {
                icon: 'flash',
                label: 'Auto-Apply',
                onPress: handleStartAutoApply,
                color: '#8b5cf6',
              },
              ...(existingMatch?.status === 'interviewing'
                ? [
                    {
                      icon: 'briefcase-check',
                      label: 'Interview Prep',
                      onPress: handleStartInterviewPrep,
                      color: '#3b82f6',
                    },
                  ]
                : []),
            ]}
            onStateChange={({ open }) => setFabOpen(open)}
            onPress={() => {
              if (fabOpen) {
                // Do something on close if needed
              }
            }}
            fabStyle={styles.fab}
            style={styles.fabGroup}
          />
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
  explanationBox: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#f5f3ff',
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#8b5cf6',
  },
  explanationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 8,
  },
  explanationTitle: {
    color: '#6d28d9',
    fontWeight: '600',
  },
  explanationText: {
    color: '#4b5563',
    lineHeight: 20,
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
    marginHorizontal: 16,
    borderRadius: 16,
    width: '92%',
    padding: 20,
    elevation: 5,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  modalHeaderText: {
    flex: 1,
    marginRight: 12,
  },
  closeIconButton: {
    padding: 4,
    marginTop: -4,
    marginRight: -4,
  },
  modalTitle: {
    fontWeight: '700',
    marginBottom: 4,
  },
  modalSubtitle: {
    color: '#6b7280',
  },
  proposalContent: {
    // Container for proposal text + action buttons
  },
  proposalScroll: {
    maxHeight: 280,
    marginBottom: 16,
  },
  proposalInput: {
    backgroundColor: '#f9fafb',
    minHeight: 200,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  modalButton: {
    flex: 1,
  },
  modalButtonContent: {
    paddingVertical: 6,
  },
  primaryButton: {
    flex: 1.5,
  },
  generateContainer: {
    paddingVertical: 24,
    alignItems: 'center',
    gap: 16,
  },
  generateButtonContent: {
    paddingVertical: 8,
    paddingHorizontal: 24,
  },
  cancelButton: {
    marginTop: 8,
  },
  // Tone selector styles
  toneSelector: {
    width: '100%',
    marginBottom: 8,
  },
  toneSelectorLabel: {
    color: '#374151',
    marginBottom: 8,
  },
  styleDropdown: {
    minWidth: 140,
  },
  styleDropdownContent: {
    flexDirection: 'row-reverse',
  },
  // Progress styles
  progressContainer: {
    width: '100%',
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  progressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  progressStep: {
    color: '#1e40af',
    flex: 1,
  },
  progressBar: {
    marginTop: 8,
    height: 4,
    borderRadius: 2,
  },
  // Error banner styles
  errorBanner: {
    width: '100%',
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  errorBannerText: {
    color: '#dc2626',
    flex: 1,
  },
  dismissLabel: {
    fontSize: 12,
  },
  // Key points styles
  keyPointsContainer: {
    marginBottom: 12,
  },
  keyPointsLabel: {
    color: '#374151',
    marginBottom: 8,
  },
  keyPointsChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  keyPointChip: {
    backgroundColor: '#dcfce7',
  },
  keyPointChipText: {
    fontSize: 11,
    color: '#166534',
  },
  // Interview Prep section styles
  interviewPrepSection: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#eff6ff',
    borderWidth: 1,
    borderColor: '#bfdbfe',
  },
  interviewPrepHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  interviewPrepHeaderText: {
    marginLeft: 12,
    flex: 1,
  },
  interviewPrepSubtitle: {
    color: '#3b82f6',
    marginTop: 2,
  },
  interviewPrepButton: {
    backgroundColor: '#3b82f6',
  },
  // Interview Prep modal styles
  interviewPrepModalContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  interviewPrepModalOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  interviewPrepModal: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    borderRadius: 16,
    width: '92%',
    maxHeight: '85%',
    elevation: 5,
    padding: 20,
  },
  interviewPrepError: {
    paddingVertical: 32,
    alignItems: 'center',
    gap: 16,
  },
  interviewPrepErrorText: {
    color: '#dc2626',
    textAlign: 'center',
  },
  interviewPrepContent: {
    paddingBottom: 8,
  },
  interviewPrepSection2: {
    marginBottom: 20,
  },
  interviewPrepSectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 12,
  },
  focusAreasContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  focusAreaChip: {
    backgroundColor: '#dbeafe',
  },
  prepTipItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  prepTipText: {
    color: '#374151',
    flex: 1,
    lineHeight: 22,
  },
  questionCard: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#f9fafb',
    marginBottom: 12,
  },
  questionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  questionMeta: {
    flexDirection: 'row',
    gap: 8,
  },
  difficultyChip: {
    height: 24,
  },
  typeChip: {
    height: 24,
    backgroundColor: '#e5e7eb',
  },
  typeChipText: {
    fontSize: 10,
    color: '#374151',
  },
  questionText: {
    color: '#111827',
    fontWeight: '500',
    lineHeight: 22,
  },
  questionExpanded: {
    marginTop: 12,
  },
  questionDivider: {
    marginBottom: 12,
  },
  questionTips: {
    marginBottom: 12,
  },
  questionTipsLabel: {
    color: '#374151',
    marginBottom: 8,
  },
  questionTip: {
    color: '#6b7280',
    marginBottom: 4,
    paddingLeft: 8,
  },
  sampleAnswer: {
    backgroundColor: '#ecfdf5',
    padding: 12,
    borderRadius: 8,
  },
  sampleAnswerLabel: {
    color: '#166534',
    marginBottom: 8,
  },
  sampleAnswerText: {
    color: '#166534',
    lineHeight: 20,
  },
  // Salary Research section styles
  salaryResearchSection: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#ecfdf5',
    borderWidth: 1,
    borderColor: '#a7f3d0',
  },
  salaryResearchHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  salaryResearchHeaderText: {
    marginLeft: 12,
    flex: 1,
  },
  salaryResearchSubtitle: {
    color: '#10b981',
    marginTop: 2,
  },
  salaryResearchButton: {
    backgroundColor: '#10b981',
  },
  // Salary Research modal styles
  salaryModalContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  salaryModalOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  salaryModal: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    borderRadius: 16,
    width: '92%',
    maxHeight: '85%',
    elevation: 5,
    padding: 20,
  },
  salaryError: {
    paddingVertical: 32,
    alignItems: 'center',
    gap: 16,
  },
  salaryErrorText: {
    color: '#dc2626',
    textAlign: 'center',
  },
  salaryContent: {
    paddingBottom: 8,
  },
  salarySection: {
    marginBottom: 20,
  },
  salarySectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 12,
  },
  salaryRangeCard: {
    backgroundColor: '#ecfdf5',
    borderRadius: 12,
    padding: 16,
  },
  salaryRangeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  salaryRangeLabel: {
    color: '#6b7280',
    fontSize: 12,
  },
  salaryRangeValues: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  salaryValueLow: {
    alignItems: 'flex-start',
  },
  salaryValueMedian: {
    alignItems: 'center',
  },
  salaryValueHigh: {
    alignItems: 'flex-end',
  },
  salaryBar: {
    height: 8,
    backgroundColor: '#d1fae5',
    borderRadius: 4,
    position: 'relative',
  },
  salaryBarFill: {
    position: 'absolute',
    left: '20%',
    right: '20%',
    top: 0,
    bottom: 0,
    backgroundColor: '#10b981',
    borderRadius: 4,
  },
  salaryBarMarker: {
    position: 'absolute',
    top: -4,
    left: '50%',
    marginLeft: -8,
    width: 16,
    height: 16,
    backgroundColor: '#059669',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#fff',
  },
  factorItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  factorText: {
    color: '#374151',
    flex: 1,
    lineHeight: 22,
  },
  comparableRolesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  comparableRoleChip: {
    backgroundColor: '#f3f4f6',
  },
  negotiationTipItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 10,
  },
  negotiationTipText: {
    color: '#374151',
    flex: 1,
    lineHeight: 22,
  },
  totalCompCard: {
    backgroundColor: '#f0fdf4',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  totalCompValue: {
    color: '#059669',
    fontWeight: '700',
    marginBottom: 8,
  },
  adjustmentText: {
    color: '#6b7280',
    marginTop: 4,
  },
  scriptCard: {
    backgroundColor: '#fffbeb',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  scriptScenario: {
    color: '#92400e',
    fontWeight: '600',
    marginBottom: 6,
  },
  scriptText: {
    color: '#78350f',
    lineHeight: 20,
  },
  // Skill Gap Analysis section styles
  skillGapSection: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#f5f3ff',
    borderWidth: 1,
    borderColor: '#c4b5fd',
  },
  skillGapHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  skillGapHeaderText: {
    marginLeft: 12,
    flex: 1,
  },
  skillGapSubtitle: {
    color: '#8b5cf6',
    marginTop: 2,
  },
  skillGapButton: {
    backgroundColor: '#8b5cf6',
  },
  // Skill Gap modal styles
  skillGapModalContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  skillGapModalOverlay: {
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    flex: 1,
  },
  skillGapModal: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    borderRadius: 16,
    width: '92%',
    maxHeight: '85%',
    elevation: 5,
    padding: 20,
  },
  skillGapError: {
    paddingVertical: 32,
    alignItems: 'center',
    gap: 16,
  },
  skillGapErrorText: {
    color: '#dc2626',
    textAlign: 'center',
  },
  skillGapContent: {
    paddingBottom: 8,
  },
  skillGapScoreSection: {
    alignItems: 'center',
    marginBottom: 24,
  },
  skillGapScoreCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#f5f3ff',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#8b5cf6',
  },
  skillGapScoreValue: {
    color: '#8b5cf6',
    fontWeight: '700',
  },
  skillGapScoreLabel: {
    color: '#6b7280',
    marginTop: 8,
  },
  skillGapResultSection: {
    marginBottom: 20,
  },
  skillGapSectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 12,
  },
  skillGapChipsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  matchedSkillChip: {
    backgroundColor: '#dcfce7',
  },
  missingSkillItem: {
    backgroundColor: '#fef3c7',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  missingSkillHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  missingSkillName: {
    color: '#111827',
    fontWeight: '600',
  },
  importanceChip: {
    height: 24,
  },
  requiredChip: {
    backgroundColor: '#fecaca',
  },
  preferredChip: {
    backgroundColor: '#fde68a',
  },
  importanceChipText: {
    fontSize: 10,
  },
  currentLevelText: {
    color: '#6b7280',
    marginBottom: 8,
  },
  resourcesList: {
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#fcd34d',
    paddingTop: 8,
  },
  resourceItem: {
    color: '#92400e',
    marginBottom: 4,
    fontSize: 12,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 10,
  },
  recommendationText: {
    color: '#374151',
    flex: 1,
    lineHeight: 22,
  },
  // Network Intelligence section styles
  networkIntelSection: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#f0f9ff',
    borderWidth: 1,
    borderColor: '#7dd3fc',
  },
  networkIntelHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  networkIntelHeaderText: {
    marginLeft: 12,
    flex: 1,
  },
  networkIntelSubtitle: {
    color: '#0284c7',
    marginTop: 2,
  },
  networkIntelButton: {
    backgroundColor: '#0ea5e9',
  },
  // Network Intelligence modal styles
  networkModalContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  networkModalOverlay: {
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    flex: 1,
  },
  networkModal: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    borderRadius: 16,
    width: '92%',
    maxHeight: '85%',
    elevation: 5,
    padding: 20,
  },
  networkError: {
    paddingVertical: 32,
    alignItems: 'center',
    gap: 16,
  },
  networkErrorText: {
    color: '#dc2626',
    textAlign: 'center',
  },
  networkContent: {
    paddingBottom: 8,
    maxHeight: 500,
  },
  networkResultSection: {
    marginBottom: 20,
  },
  networkSectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 12,
  },
  networkInsightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  networkInsightText: {
    color: '#374151',
    flex: 1,
    lineHeight: 20,
  },
  networkNewsItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 10,
    backgroundColor: '#faf5ff',
    padding: 10,
    borderRadius: 8,
  },
  networkNewsText: {
    color: '#374151',
    flex: 1,
    lineHeight: 20,
  },
  networkTrendItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  networkTrendText: {
    color: '#374151',
    flex: 1,
    lineHeight: 20,
  },
  connectionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
    backgroundColor: '#f0f9ff',
    padding: 12,
    borderRadius: 10,
  },
  connectionAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#e0f2fe',
    justifyContent: 'center',
    alignItems: 'center',
  },
  connectionText: {
    color: '#0c4a6e',
    flex: 1,
    fontWeight: '500',
  },
  connectionDetails: {
    flex: 1,
    marginLeft: 12,
  },
  connectionSubtext: {
    color: '#64748b',
    marginTop: 4,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  templateCard: {
    backgroundColor: '#f5f3ff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  templateTitle: {
    color: '#5b21b6',
    fontWeight: '600',
    marginBottom: 4,
  },
  templatePlatform: {
    color: '#7c3aed',
    marginBottom: 8,
  },
  templateMessage: {
    color: '#4c1d95',
    lineHeight: 22,
  },
  outreachItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    marginBottom: 12,
    backgroundColor: '#fefce8',
    padding: 12,
    borderRadius: 8,
  },
  outreachText: {
    color: '#713f12',
    flex: 1,
    lineHeight: 22,
  },
  // Auto-Apply section styles
  autoApplySection: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#faf5ff',
    borderWidth: 1,
    borderColor: '#c4b5fd',
  },
  autoApplyHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  autoApplyHeaderText: {
    marginLeft: 12,
    flex: 1,
  },
  autoApplySubtitle: {
    color: '#7c3aed',
    marginTop: 2,
  },
  autoApplyButton: {
    backgroundColor: '#8b5cf6',
  },
  // Auto-Apply modal styles
  autoApplyModalContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  autoApplyModalOverlay: {
    flex: 1,
    width: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  autoApplyModal: {
    width: '100%',
    maxHeight: '90%',
    borderRadius: 16,
    backgroundColor: '#ffffff',
    padding: 20,
  },
  autoApplyModalContent: {
    overflow: 'hidden',
    borderRadius: 16,
  },
  autoApplyError: {
    paddingVertical: 32,
    alignItems: 'center',
    gap: 16,
  },
  autoApplyErrorText: {
    color: '#dc2626',
    textAlign: 'center',
  },
  autoApplyContent: {
    maxHeight: 500,
    paddingBottom: 8,
  },
  autoApplyResultSection: {
    marginBottom: 24,
  },
  autoApplySectionTitle: {
    color: '#374151',
    fontWeight: '600',
    marginBottom: 16,
  },
  fitScoreContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  fitScoreCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#ede9fe',
    borderWidth: 4,
    borderColor: '#8b5cf6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  fitScoreText: {
    color: '#7c3aed',
    fontWeight: '700',
  },
  fitScoreLabel: {
    color: '#6b7280',
  },
  fitSubsection: {
    marginBottom: 16,
  },
  fitSubsectionTitle: {
    color: '#374151',
    fontWeight: '600',
    marginBottom: 10,
  },
  strengthItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
    backgroundColor: '#f0fdf4',
    padding: 10,
    borderRadius: 8,
  },
  strengthText: {
    color: '#166534',
    flex: 1,
    lineHeight: 20,
  },
  gapItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
    backgroundColor: '#fefce8',
    padding: 10,
    borderRadius: 8,
  },
  gapText: {
    color: '#854d0e',
    flex: 1,
    lineHeight: 20,
  },
  materialCard: {
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  materialHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 12,
  },
  materialTitle: {
    color: '#374151',
    fontWeight: '600',
  },
  materialPreview: {
    color: '#6b7280',
    lineHeight: 22,
    fontStyle: 'italic',
  },
  highlightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  highlightText: {
    color: '#374151',
    flex: 1,
    lineHeight: 20,
  },
  screeningItem: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  screeningQuestion: {
    color: '#374151',
    fontWeight: '600',
    marginBottom: 6,
  },
  screeningAnswer: {
    color: '#6b7280',
    lineHeight: 22,
  },
  // AI Badge and FAB styles
  agentTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  aiBadge: {
    backgroundColor: '#eef2ff',
    height: 22,
  },
  aiBadgeText: {
    fontSize: 10,
    color: '#6366f1',
    fontWeight: '600',
  },
  fab: {
    backgroundColor: '#6366f1',
    marginBottom: 80,
  },
  fabGroup: {
    paddingBottom: 0,
  },
  modeToggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#f3f4f6',
    borderRadius: 8,
    padding: 4,
    marginBottom: 16,
  },
  modeToggle: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
  },
  modeToggleActive: {
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  modeToggleText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#6b7280',
  },
  modeToggleTextActive: {
    color: '#3b82f6',
  },
  saveFirstContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    gap: 16,
  },
  saveFirstText: {
    color: '#6b7280',
    textAlign: 'center',
  },
});
