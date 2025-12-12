import React from 'react';
import { View, StyleSheet, ScrollView, Alert, Linking } from 'react-native';
import {
  Text,
  Button,
  Card,
  Avatar,
  List,
  Divider,
  Switch,
  ActivityIndicator,
} from 'react-native-paper';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '../../src/contexts/AuthContext';
import { useProfile, useUpdateProfile } from '../../src/hooks/useJobs';
import { resumeApi } from '../../src/api/client';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout, isLoading } = useAuth();
  const { data: profile, isLoading: isLoadingProfile, refetch: refetchProfile } = useProfile();
  const updateProfile = useUpdateProfile();
  const [pushNotifications, setPushNotifications] = React.useState(true);
  const [isUploadingResume, setIsUploadingResume] = React.useState(false);

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
      setIsUploadingResume(true);

      await resumeApi.uploadResume({
        uri: file.uri,
        name: file.name,
        type: file.mimeType || 'application/pdf',
      });

      Alert.alert('Success', 'Resume uploaded successfully');
      refetchProfile();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to upload resume');
    } finally {
      setIsUploadingResume(false);
    }
  };

  const handleViewResume = () => {
    if (user?.resume?.url) {
      Linking.openURL(user.resume.url);
    } else {
      Alert.alert('Resume', 'Resume preview not available');
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
          <Avatar.Text
            size={80}
            label={getInitials(user?.full_name, user?.email)}
            style={styles.avatar}
          />
          <View style={styles.profileInfo}>
            <Text variant="titleLarge" style={styles.name}>
              {user?.full_name || 'No name set'}
            </Text>
            <Text variant="bodyMedium" style={styles.email}>
              {user?.email}
            </Text>
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
          <>
            <List.Item
              title={user.resume.file_name || 'Resume uploaded'}
              description={`Uploaded ${new Date(user.resume.uploaded_at).toLocaleDateString()}`}
              left={(props) => <List.Icon {...props} icon="file-document" />}
              right={() => <List.Icon icon="chevron-right" />}
              onPress={handleViewResume}
            />
            <Divider />
            <View style={styles.resumeActions}>
              <Button mode="outlined" onPress={handleViewResume} style={styles.resumeButton}>
                View
              </Button>
              <Button
                mode="outlined"
                onPress={handleUploadResume}
                style={styles.resumeButton}
                loading={isUploadingResume}
              >
                Replace
              </Button>
            </View>
          </>
        ) : (
          <View style={styles.noResume}>
            <Text variant="bodyMedium" style={styles.noResumeText}>
              No resume uploaded
            </Text>
            <Button
              mode="contained"
              onPress={handleUploadResume}
              icon="upload"
              loading={isUploadingResume}
            >
              Upload Resume
            </Button>
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
  editButton: {
    marginTop: 8,
  },
  sectionCard: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  noResume: {
    padding: 16,
    alignItems: 'center',
  },
  noResumeText: {
    color: '#6b7280',
    marginBottom: 12,
  },
  resumeActions: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
  },
  resumeButton: {
    flex: 1,
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
});
