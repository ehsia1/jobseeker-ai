import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, Alert, Linking, TouchableOpacity, Pressable, Image } from 'react-native';
import {
  Text,
  Button,
  Card,
  Avatar,
  List,
  Divider,
  Switch,
  ActivityIndicator,
  ProgressBar,
  Portal,
  Modal,
  Chip,
} from 'react-native-paper';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../src/contexts/AuthContext';
import { useProfile, useUpdateProfile, useUploadResume, useReparseResume, useSubmitResumeText } from '../../src/hooks/useJobs';
import { API_URL } from '../../src/api/client';

// Get full avatar URL from relative path
function getAvatarUrl(profilePictureUrl: string | null | undefined): string | null {
  if (!profilePictureUrl) return null;
  if (profilePictureUrl.startsWith('http')) return profilePictureUrl;
  return `${API_URL}${profilePictureUrl}`;
}

// Format phone number for display: (555) 555-5555
function formatPhoneNumber(value: string | null | undefined): string | null {
  if (!value) return null;
  const digits = value.replace(/\D/g, '');
  if (digits.length === 0) return null;
  if (digits.length <= 3) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
}
import { useResumeOptimizer } from '../../src/hooks/useAgent';
import type { ResumeOptimizeSuggestion } from '@jobseeker/shared';
import { TextInput as RNTextInput } from 'react-native';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout, isLoading, refreshUser } = useAuth();
  const { data: profile, isLoading: isLoadingProfile, refetch: refetchProfile } = useProfile();
  const updateProfile = useUpdateProfile();
  const uploadResume = useUploadResume();
  const reparseResume = useReparseResume();
  const submitResumeText = useSubmitResumeText();
  const [pushNotifications, setPushNotifications] = React.useState(true);
  const [optimizeModalVisible, setOptimizeModalVisible] = useState(false);
  const [pasteTextModalVisible, setPasteTextModalVisible] = useState(false);
  const [resumeText, setResumeText] = useState('');

  // Resume Optimizer agent
  const resumeOptimize = useResumeOptimizer();

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: logout },
    ]);
  };

  const getInitials = (name?: string | null, email?: string) => {
    if (name) {
      return name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    return email?.slice(0, 2).toUpperCase() || '??';
  };

  const handleEditProfile = () => {
    router.push('/profile/edit');
  };

  const handleToggleRemoteOnly = async () => {
    const newValue = !profile?.preferences?.remote_only;
    try {
      await updateProfile.mutateAsync({
        preferences: {
          ...profile?.preferences,
          remote_only: newValue,
        },
      });
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to update preference');
    }
  };

  const handleUploadResume = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets?.[0]) {
        return;
      }

      const file = result.assets[0];

      // Use the mutation hook which handles cache invalidation
      await uploadResume.mutateAsync({
        uri: file.uri,
        name: file.name,
        type: file.mimeType || 'application/pdf',
      });

      Alert.alert('Success', 'Resume uploaded and parsed successfully! View your resume to see the extracted data.');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to upload resume');
    }
  };

  const handleReparseResume = async () => {
    try {
      await reparseResume.mutateAsync();
      Alert.alert('Success', 'Resume re-parsed with updated logic! View your resume to see the refreshed data.');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to re-parse resume');
    }
  };

  const handleViewResume = () => {
    router.push('/resume/view');
  };

  const handleSubmitResumeText = async () => {
    if (!resumeText.trim() || resumeText.trim().length < 100) {
      Alert.alert('Error', 'Please paste at least 100 characters of resume content.');
      return;
    }

    try {
      await submitResumeText.mutateAsync(resumeText.trim());
      setPasteTextModalVisible(false);
      setResumeText('');
      Alert.alert('Success', 'Resume text parsed successfully! Your profile has been updated.');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to parse resume text');
    }
  };

  const handleOptimizeResume = () => {
    if (!user?.resume) {
      Alert.alert('No Resume', 'Please upload a resume first to optimize it.');
      return;
    }
    setOptimizeModalVisible(true);
    resumeOptimize.run({});
  };

  const getSuggestionPriorityColor = (priority: string) => {
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

  const handleSubscription = () => {
    router.push('/subscription');
  };

  const handlePrivacyPolicy = () => {
    Linking.openURL('https://jobseeker.ai/privacy');
  };

  const handleTermsOfService = () => {
    Linking.openURL('https://jobseeker.ai/terms');
  };

  return (
    <ScrollView style={styles.container}>
      <Card style={styles.profileCard}>
        <View style={styles.profileHeader}>
          {user?.profile_picture_url ? (
            <Image
              source={{ uri: getAvatarUrl(user.profile_picture_url)! }}
              style={styles.avatarImage}
            />
          ) : (
            <Avatar.Text
              size={80}
              label={getInitials(user?.full_name, user?.email)}
              style={styles.avatar}
            />
          )}
          <View style={styles.profileInfo}>
            <Text variant="titleLarge" style={styles.name}>
              {user?.full_name || 'No name set'}
            </Text>
            <Text variant="bodyMedium" style={styles.email}>
              {user?.email}
            </Text>
            {user?.phone && (
              <Text variant="bodyMedium" style={styles.phone}>
                {formatPhoneNumber(user.phone)}
              </Text>
            )}
          </View>
        </View>
        <Button
          mode="outlined"
          onPress={handleEditProfile}
          style={styles.editButton}
          icon="pencil"
        >
          Edit Profile
        </Button>
      </Card>

      <Card style={styles.sectionCard}>
        <Card.Title title="Job Preferences" titleVariant="titleMedium" />
        <Divider />
        <List.Item
          title="Profession"
          description={profile?.profession || 'Not set'}
          left={(props) => <List.Icon {...props} icon="briefcase" />}
          right={() => <List.Icon icon="chevron-right" />}
          onPress={handleEditProfile}
        />
        <Divider />
        <List.Item
          title="Skills"
          description={
            profile?.skills?.slice(0, 3).join(', ') || 'Not set'
          }
          left={(props) => <List.Icon {...props} icon="star" />}
          right={() => <List.Icon icon="chevron-right" />}
          onPress={handleEditProfile}
        />
        <Divider />
        <List.Item
          title="Rate Preferences"
          description={
            profile?.min_rate_usd
              ? `$${profile.min_rate_usd}+/hr`
              : 'Not set'
          }
          left={(props) => <List.Icon {...props} icon="cash" />}
          right={() => <List.Icon icon="chevron-right" />}
          onPress={handleEditProfile}
        />
        <Divider />
        <List.Item
          title="Remote Only"
          description={
            profile?.preferences?.remote_only
              ? 'Only showing remote jobs'
              : 'Showing all jobs'
          }
          left={(props) => <List.Icon {...props} icon="home" />}
          right={() => (
            <Switch
              value={profile?.preferences?.remote_only || false}
              onValueChange={handleToggleRemoteOnly}
            />
          )}
        />
      </Card>

      <Card style={styles.sectionCard}>
        <Card.Title title="Resume" titleVariant="titleMedium" />
        <Divider />
        {user?.resume ? (
          <View>
            <List.Item
              title={user.resume.file_name || 'Resume uploaded'}
              description={`Uploaded ${new Date(user.resume.uploaded_at).toLocaleDateString()}`}
              left={(props) => <List.Icon {...props} icon="file-document" />}
              right={() => <List.Icon icon="chevron-right" />}
              onPress={handleViewResume}
            />
            {/* Resume Stats */}
            <View style={styles.resumeStats}>
              <View style={styles.resumeStat}>
                <Text variant="titleMedium" style={styles.resumeStatValue}>
                  {user.resume.work_experience_count ?? 0}
                </Text>
                <Text variant="bodySmall" style={styles.resumeStatLabel}>
                  Jobs
                </Text>
              </View>
              <View style={styles.resumeStat}>
                <Text variant="titleMedium" style={styles.resumeStatValue}>
                  {user.resume.total_experience_years ?? 0}
                </Text>
                <Text variant="bodySmall" style={styles.resumeStatLabel}>
                  Years Exp
                </Text>
              </View>
              <View style={styles.resumeStat}>
                <Text variant="titleMedium" style={[
                  styles.resumeStatValue,
                  { color: (user.resume.parse_quality_score ?? 0) >= 70 ? '#10b981' : '#f59e0b' }
                ]}>
                  {user.resume.parse_quality_score ?? 0}%
                </Text>
                <Text variant="bodySmall" style={styles.resumeStatLabel}>
                  Parse Quality
                </Text>
              </View>
            </View>

            {/* Low Parse Quality Warning */}
            {(user.resume.parse_quality_score ?? 0) < 50 && (
              <View style={styles.parseWarning}>
                <View style={styles.parseWarningHeader}>
                  <Ionicons name="warning" size={20} color="#d97706" />
                  <Text variant="titleSmall" style={styles.parseWarningTitle}>
                    Low Parse Quality Detected
                  </Text>
                </View>
                <Text variant="bodySmall" style={styles.parseWarningText}>
                  Your resume may not have extracted correctly. This can happen with complex PDF layouts or image-based resumes.
                </Text>
                <Text variant="bodySmall" style={styles.parseWarningSuggestion}>
                  Try one of these options:
                </Text>
                <View style={styles.parseWarningOptions}>
                  <Text variant="bodySmall" style={styles.parseWarningOption}>
                    • Paste your resume text directly (most reliable)
                  </Text>
                  <Text variant="bodySmall" style={styles.parseWarningOption}>
                    • Upload a simpler PDF format
                  </Text>
                  <Text variant="bodySmall" style={styles.parseWarningOption}>
                    • Try the Re-parse button after uploading
                  </Text>
                </View>
                <Button
                  mode="contained"
                  onPress={() => setPasteTextModalVisible(true)}
                  style={styles.parseWarningButton}
                  icon="text-box-outline"
                  buttonColor="#d97706"
                >
                  Paste Resume Text
                </Button>
              </View>
            )}

            <Divider />
            <View style={styles.resumeActions}>
              <Button mode="outlined" onPress={handleViewResume} style={styles.resumeButton} icon="eye">
                View
              </Button>
              <Button
                mode="outlined"
                onPress={handleUploadResume}
                style={styles.resumeButton}
                loading={uploadResume.isPending}
                icon="cloud-upload"
              >
                Replace
              </Button>
              <Button
                mode="outlined"
                onPress={handleReparseResume}
                style={styles.resumeButton}
                loading={reparseResume.isPending}
                icon="refresh"
              >
                Re-parse
              </Button>
            </View>
            <View style={styles.resumeSecondaryActions}>
              <Button
                mode="text"
                onPress={() => setPasteTextModalVisible(true)}
                icon="text-box-outline"
                compact
              >
                Paste Text Instead
              </Button>
            </View>
            <Button
              mode="contained"
              onPress={handleOptimizeResume}
              style={styles.optimizeButton}
              icon="auto-fix"
              loading={resumeOptimize.isRunning}
            >
              {resumeOptimize.isRunning ? 'Analyzing...' : 'Optimize Resume'}
            </Button>
          </View>
        ) : (
          <View style={styles.noResume}>
            <Ionicons name="document-text-outline" size={48} color="#9ca3af" style={{ marginBottom: 12 }} />
            <Text variant="bodyMedium" style={styles.noResumeText}>
              No resume uploaded yet
            </Text>
            <Text variant="bodySmall" style={styles.noResumeHint}>
              Upload from your device, Google Drive, iCloud, or Dropbox
            </Text>
            <View style={styles.uploadOptions}>
              <Button
                mode="contained"
                onPress={handleUploadResume}
                icon="cloud-upload"
                loading={uploadResume.isPending}
                style={styles.uploadButton}
              >
                Upload Resume
              </Button>
              <Button
                mode="outlined"
                onPress={() => setPasteTextModalVisible(true)}
                icon="text-box-outline"
                style={styles.pasteButton}
              >
                Paste Text
              </Button>
            </View>
            <View style={styles.supportedFormats}>
              <Ionicons name="information-circle-outline" size={14} color="#9ca3af" />
              <Text variant="bodySmall" style={styles.supportedFormatsText}>
                Supports PDF, DOC, DOCX (max 10MB)
              </Text>
            </View>
          </View>
        )}
      </Card>

      <Card style={styles.sectionCard}>
        <Card.Title title="Subscription" titleVariant="titleMedium" />
        <Divider />
        <List.Item
          title={user?.subscription?.tier || 'Free'}
          description={
            user?.subscription?.tier === 'free'
              ? 'Upgrade for more features'
              : `Renews ${new Date(user?.subscription?.current_period_end || '').toLocaleDateString()}`
          }
          left={(props) => <List.Icon {...props} icon="crown" />}
          right={() => <List.Icon icon="chevron-right" />}
          onPress={handleSubscription}
        />
      </Card>

      <Card style={styles.sectionCard}>
        <Card.Title title="Settings" titleVariant="titleMedium" />
        <Divider />
        <List.Item
          title="Push Notifications"
          description="Get notified about new job matches"
          left={(props) => <List.Icon {...props} icon="bell" />}
          right={() => (
            <Switch
              value={pushNotifications}
              onValueChange={setPushNotifications}
            />
          )}
        />
        <Divider />
        <List.Item
          title="Privacy Policy"
          left={(props) => <List.Icon {...props} icon="shield-account" />}
          right={() => <List.Icon icon="chevron-right" />}
          onPress={handlePrivacyPolicy}
        />
        <Divider />
        <List.Item
          title="Terms of Service"
          left={(props) => <List.Icon {...props} icon="file-document" />}
          right={() => <List.Icon icon="chevron-right" />}
          onPress={handleTermsOfService}
        />
      </Card>

      <Button
        mode="outlined"
        onPress={handleLogout}
        loading={isLoading}
        style={styles.logoutButton}
        textColor="#dc2626"
      >
        Sign Out
      </Button>

      <Text variant="bodySmall" style={styles.version}>
        JobSeeker AI v1.0.0
      </Text>

      {/* Resume Optimizer Modal */}
      <Portal>
        <Modal
          visible={optimizeModalVisible}
          onDismiss={() => {
            setOptimizeModalVisible(false);
            resumeOptimize.reset();
          }}
          contentContainerStyle={styles.optimizeModalContent}
        >
          <View style={styles.optimizeModalHeader}>
            <Text variant="titleLarge" style={styles.optimizeModalTitle}>
              Resume Analysis
            </Text>
            <TouchableOpacity
              onPress={() => {
                setOptimizeModalVisible(false);
                resumeOptimize.reset();
              }}
            >
              <Ionicons name="close" size={24} color="#6b7280" />
            </TouchableOpacity>
          </View>

          {/* Loading State */}
          {resumeOptimize.isRunning && (
            <View style={styles.optimizeLoading}>
              <ActivityIndicator size="large" color="#3b82f6" />
              <Text variant="bodyMedium" style={styles.optimizeLoadingText}>
                {resumeOptimize.currentStep || 'Analyzing your resume...'}
              </Text>
              <ProgressBar
                progress={resumeOptimize.progress / 100}
                color="#3b82f6"
                style={styles.optimizeProgress}
              />
            </View>
          )}

          {/* Error State */}
          {resumeOptimize.isFailed && (
            <View style={styles.optimizeError}>
              <Ionicons name="alert-circle" size={48} color="#dc2626" />
              <Text variant="bodyMedium" style={styles.optimizeErrorText}>
                {resumeOptimize.errors[0] || 'Failed to analyze resume'}
              </Text>
              <Button mode="outlined" onPress={() => resumeOptimize.run({})}>
                Try Again
              </Button>
            </View>
          )}

          {/* Results */}
          {resumeOptimize.isCompleted && resumeOptimize.result && (
            <ScrollView style={styles.optimizeResults}>
              {/* ATS Score */}
              <View style={styles.atsScoreContainer}>
                <View style={styles.atsScoreCircle}>
                  <Text variant="headlineLarge" style={styles.atsScoreText}>
                    {resumeOptimize.result.ats_score}
                  </Text>
                  <Text variant="bodySmall" style={styles.atsScoreLabel}>
                    ATS Score
                  </Text>
                </View>
                <Text variant="bodyMedium" style={styles.atsScoreDescription}>
                  {resumeOptimize.result.ats_score >= 80
                    ? 'Great! Your resume is well-optimized for ATS systems.'
                    : resumeOptimize.result.ats_score >= 60
                    ? 'Good, but there is room for improvement.'
                    : 'Your resume needs optimization for better ATS compatibility.'}
                </Text>
              </View>

              {/* Suggestions */}
              {resumeOptimize.result.suggestions && resumeOptimize.result.suggestions.length > 0 && (
                <View style={styles.suggestionsContainer}>
                  <Text variant="titleMedium" style={styles.sectionTitle}>
                    Suggestions
                  </Text>
                  {resumeOptimize.result.suggestions.map((suggestion: ResumeOptimizeSuggestion, index: number) => (
                    <View key={index} style={styles.suggestionItem}>
                      <View style={styles.suggestionHeader}>
                        <Chip
                          style={[
                            styles.priorityChip,
                            { backgroundColor: getSuggestionPriorityColor(suggestion.priority) + '20' },
                          ]}
                          textStyle={[
                            styles.priorityChipText,
                            { color: getSuggestionPriorityColor(suggestion.priority) },
                          ]}
                        >
                          {suggestion.priority}
                        </Chip>
                        <Text variant="bodySmall" style={styles.suggestionSection}>
                          {suggestion.category}
                        </Text>
                      </View>
                      <Text variant="bodyMedium" style={styles.suggestionIssue}>
                        {suggestion.issue}
                      </Text>
                      <Text variant="bodySmall" style={styles.suggestionFix}>
                        💡 {suggestion.fix}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Keywords */}
              <View style={styles.keywordsContainer}>
                {resumeOptimize.result.keywords_missing && resumeOptimize.result.keywords_missing.length > 0 && (
                  <View style={styles.keywordSection}>
                    <Text variant="titleSmall" style={styles.keywordTitle}>
                      Missing Keywords
                    </Text>
                    <View style={styles.keywordChips}>
                      {resumeOptimize.result.keywords_missing.map((keyword: string, index: number) => (
                        <Chip key={index} style={styles.missingKeywordChip} textStyle={styles.missingKeywordText}>
                          {keyword}
                        </Chip>
                      ))}
                    </View>
                  </View>
                )}

                {resumeOptimize.result.keywords_present && resumeOptimize.result.keywords_present.length > 0 && (
                  <View style={styles.keywordSection}>
                    <Text variant="titleSmall" style={styles.keywordTitle}>
                      Present Keywords
                    </Text>
                    <View style={styles.keywordChips}>
                      {resumeOptimize.result.keywords_present.map((keyword: string, index: number) => (
                        <Chip key={index} style={styles.presentKeywordChip} textStyle={styles.presentKeywordText}>
                          {keyword}
                        </Chip>
                      ))}
                    </View>
                  </View>
                )}
              </View>
            </ScrollView>
          )}
        </Modal>

        {/* Paste Resume Text Modal */}
        <Modal
          visible={pasteTextModalVisible}
          onDismiss={() => {
            setPasteTextModalVisible(false);
            setResumeText('');
          }}
          contentContainerStyle={styles.pasteTextModalContent}
        >
          <View style={styles.pasteTextModalHeader}>
            <Text variant="titleLarge" style={styles.pasteTextModalTitle}>
              Paste Resume Text
            </Text>
            <TouchableOpacity
              onPress={() => {
                setPasteTextModalVisible(false);
                setResumeText('');
              }}
            >
              <Ionicons name="close" size={24} color="#6b7280" />
            </TouchableOpacity>
          </View>

          <View style={styles.pasteTextInstructions}>
            <Ionicons name="information-circle-outline" size={20} color="#3b82f6" />
            <Text variant="bodySmall" style={styles.pasteTextInstructionsText}>
              Copy your resume content from Word, Google Docs, or any text editor and paste it below. This bypasses PDF extraction issues.
            </Text>
          </View>

          <RNTextInput
            style={styles.pasteTextInput}
            multiline
            placeholder="Paste your resume text here...&#10;&#10;Include your contact info, work experience, education, skills, etc."
            placeholderTextColor="#9ca3af"
            value={resumeText}
            onChangeText={setResumeText}
            textAlignVertical="top"
          />

          <View style={styles.pasteTextCharCount}>
            <Text variant="bodySmall" style={[
              styles.pasteTextCharCountText,
              { color: resumeText.length >= 100 ? '#10b981' : '#f59e0b' }
            ]}>
              {resumeText.length} characters {resumeText.length < 100 ? '(minimum 100)' : ''}
            </Text>
          </View>

          <View style={styles.pasteTextActions}>
            <Button
              mode="outlined"
              onPress={() => {
                setPasteTextModalVisible(false);
                setResumeText('');
              }}
              style={styles.pasteTextCancelButton}
            >
              Cancel
            </Button>
            <Button
              mode="contained"
              onPress={handleSubmitResumeText}
              style={styles.pasteTextSubmitButton}
              loading={submitResumeText.isPending}
              disabled={resumeText.trim().length < 100}
            >
              Parse Resume
            </Button>
          </View>
        </Modal>
      </Portal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  profileCard: {
    margin: 16,
    marginBottom: 8,
    padding: 16,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatar: {
    backgroundColor: '#3b82f6',
  },
  avatarImage: {
    width: 80,
    height: 80,
    borderRadius: 40,
  },
  profileInfo: {
    marginLeft: 16,
    flex: 1,
  },
  name: {
    fontWeight: '600',
    color: '#111827',
  },
  email: {
    color: '#6b7280',
    marginTop: 2,
  },
  phone: {
    color: '#6b7280',
    marginTop: 2,
  },
  editButton: {
    marginTop: 8,
  },
  sectionCard: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  noResume: {
    padding: 20,
    alignItems: 'center',
  },
  noResumeText: {
    color: '#374151',
    fontWeight: '500',
    marginBottom: 4,
  },
  noResumeHint: {
    color: '#6b7280',
    marginBottom: 16,
    textAlign: 'center',
  },
  uploadOptions: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  uploadButton: {
    flex: 1,
  },
  pasteButton: {
    flex: 1,
  },
  supportedFormats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  supportedFormatsText: {
    color: '#9ca3af',
  },
  resumeActions: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
  },
  resumeButton: {
    flex: 1,
  },
  resumeStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  resumeStat: {
    alignItems: 'center',
  },
  resumeStatValue: {
    fontWeight: '600',
    color: '#111827',
  },
  resumeStatLabel: {
    color: '#6b7280',
    marginTop: 2,
  },
  logoutButton: {
    margin: 16,
    marginTop: 24,
    borderColor: '#dc2626',
  },
  version: {
    textAlign: 'center',
    color: '#9ca3af',
    marginBottom: 32,
  },
  // Resume Optimizer styles
  optimizeButton: {
    marginHorizontal: 12,
    marginBottom: 12,
    backgroundColor: '#3b82f6',
  },
  optimizeModalContent: {
    backgroundColor: '#fff',
    margin: 16,
    borderRadius: 12,
    maxHeight: '85%',
  },
  optimizeModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  optimizeModalTitle: {
    color: '#111827',
    fontWeight: '600',
  },
  optimizeLoading: {
    padding: 32,
    alignItems: 'center',
  },
  optimizeLoadingText: {
    color: '#6b7280',
    marginTop: 16,
    marginBottom: 12,
    textAlign: 'center',
  },
  optimizeProgress: {
    width: '100%',
    height: 4,
    borderRadius: 2,
  },
  optimizeError: {
    padding: 32,
    alignItems: 'center',
  },
  optimizeErrorText: {
    color: '#dc2626',
    marginVertical: 16,
    textAlign: 'center',
  },
  optimizeResults: {
    padding: 16,
  },
  atsScoreContainer: {
    alignItems: 'center',
    marginBottom: 24,
    paddingBottom: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  atsScoreCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#dbeafe',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  atsScoreText: {
    color: '#1d4ed8',
    fontWeight: '700',
  },
  atsScoreLabel: {
    color: '#3b82f6',
    marginTop: -4,
  },
  atsScoreDescription: {
    color: '#6b7280',
    textAlign: 'center',
  },
  suggestionsContainer: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 12,
  },
  suggestionItem: {
    backgroundColor: '#f9fafb',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  suggestionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  priorityChip: {
    height: 24,
    marginRight: 8,
  },
  priorityChipText: {
    fontSize: 11,
    textTransform: 'capitalize',
  },
  suggestionSection: {
    color: '#6b7280',
    textTransform: 'capitalize',
  },
  suggestionIssue: {
    color: '#374151',
    marginBottom: 4,
  },
  suggestionFix: {
    color: '#059669',
    fontStyle: 'italic',
  },
  keywordsContainer: {
    marginBottom: 16,
  },
  keywordSection: {
    marginBottom: 16,
  },
  keywordTitle: {
    color: '#374151',
    marginBottom: 8,
  },
  keywordChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  missingKeywordChip: {
    backgroundColor: '#fef2f2',
    marginBottom: 4,
  },
  missingKeywordText: {
    color: '#dc2626',
    fontSize: 12,
  },
  presentKeywordChip: {
    backgroundColor: '#dcfce7',
    marginBottom: 4,
  },
  presentKeywordText: {
    color: '#166534',
    fontSize: 12,
  },
  // Parse warning styles
  parseWarning: {
    backgroundColor: '#fffbeb',
    padding: 12,
    marginHorizontal: 12,
    marginVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#fcd34d',
  },
  parseWarningHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  parseWarningTitle: {
    color: '#92400e',
    fontWeight: '600',
    marginLeft: 8,
  },
  parseWarningText: {
    color: '#78350f',
    marginBottom: 8,
    lineHeight: 18,
  },
  parseWarningSuggestion: {
    color: '#92400e',
    fontWeight: '500',
    marginBottom: 4,
  },
  parseWarningOptions: {
    marginBottom: 12,
  },
  parseWarningOption: {
    color: '#78350f',
    marginLeft: 8,
    lineHeight: 20,
  },
  parseWarningButton: {
    marginTop: 4,
  },
  // Resume secondary actions
  resumeSecondaryActions: {
    alignItems: 'center',
    paddingVertical: 4,
  },
  // Paste text modal styles
  pasteTextModalContent: {
    backgroundColor: '#fff',
    margin: 16,
    borderRadius: 12,
    maxHeight: '85%',
  },
  pasteTextModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  pasteTextModalTitle: {
    color: '#111827',
    fontWeight: '600',
  },
  pasteTextInstructions: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 12,
    backgroundColor: '#eff6ff',
    marginHorizontal: 16,
    marginTop: 16,
    borderRadius: 8,
    gap: 8,
  },
  pasteTextInstructionsText: {
    color: '#1e40af',
    flex: 1,
    lineHeight: 18,
  },
  pasteTextInput: {
    marginHorizontal: 16,
    marginTop: 12,
    height: 200,
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    color: '#111827',
    backgroundColor: '#f9fafb',
  },
  pasteTextCharCount: {
    marginHorizontal: 16,
    marginTop: 8,
    alignItems: 'flex-end',
  },
  pasteTextCharCountText: {
    fontSize: 12,
  },
  pasteTextActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    padding: 16,
    gap: 12,
  },
  pasteTextCancelButton: {
    minWidth: 80,
  },
  pasteTextSubmitButton: {
    minWidth: 120,
  },
});
