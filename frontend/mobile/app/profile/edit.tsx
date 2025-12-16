import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
  Image,
} from 'react-native';
import {
  Text,
  TextInput,
  Button,
  Chip,
  Switch,
  Surface,
  Avatar,
  IconButton,
} from 'react-native-paper';
import { useRouter, Stack } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { useProfile, useUpdateProfile, useUpdateUser, useUploadAvatar, useDeleteAvatar } from '../../src/hooks/useJobs';
import { useAuth } from '../../src/contexts/AuthContext';
import { API_URL } from '../../src/api/client';

// Format phone number as user types: (555) 555-5555
function formatPhoneNumber(value: string): string {
  // Strip all non-digits
  const digits = value.replace(/\D/g, '');

  // Limit to 10 digits for US numbers
  const limited = digits.slice(0, 10);

  // Format based on length
  if (limited.length === 0) return '';
  if (limited.length <= 3) return `(${limited}`;
  if (limited.length <= 6) return `(${limited.slice(0, 3)}) ${limited.slice(3)}`;
  return `(${limited.slice(0, 3)}) ${limited.slice(3, 6)}-${limited.slice(6)}`;
}

// Get full avatar URL from relative path
function getAvatarUrl(profilePictureUrl: string | null | undefined): string | null {
  if (!profilePictureUrl) return null;
  // If already a full URL, return as-is
  if (profilePictureUrl.startsWith('http')) return profilePictureUrl;
  // Otherwise, prepend API_URL
  return `${API_URL}${profilePictureUrl}`;
}

export default function EditProfileScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { data: profile, isLoading: isLoadingProfile } = useProfile();
  const updateProfile = useUpdateProfile();
  const updateUser = useUpdateUser();
  const uploadAvatar = useUploadAvatar();
  const deleteAvatar = useDeleteAvatar();

  // Personal info state
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [avatarUri, setAvatarUri] = useState<string | null>(null);

  // Form state
  const [profession, setProfession] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState('');
  const [experienceYears, setExperienceYears] = useState('');
  const [minRate, setMinRate] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);

  // Populate form with existing user and profile data
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      // Format phone number if it exists
      setPhone(user.phone ? formatPhoneNumber(user.phone) : '');
      // Convert relative avatar URL to full URL
      setAvatarUri(getAvatarUrl(user.profile_picture_url));
    }
  }, [user]);

  useEffect(() => {
    if (profile) {
      setProfession(profile.profession || '');
      setSkills(profile.skills || []);
      setExperienceYears(profile.experience_years?.toString() || '');
      setMinRate(profile.min_rate_usd?.toString() || '');
      setRemoteOnly(profile.preferences?.remote_only || false);
    }
  }, [profile]);

  const handleAddSkill = () => {
    const skill = newSkill.trim();
    if (skill && !skills.includes(skill)) {
      setSkills([...skills, skill]);
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const pickImage = async () => {
    // Request permission
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Please allow access to your photo library to upload a profile picture.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      try {
        await uploadAvatar.mutateAsync({
          uri: asset.uri,
          name: `avatar.${asset.uri.split('.').pop() || 'jpg'}`,
          type: asset.mimeType || 'image/jpeg',
        });
        setAvatarUri(asset.uri);
        Alert.alert('Success', 'Profile picture updated!');
      } catch (error: any) {
        Alert.alert('Error', error.message || 'Failed to upload profile picture');
      }
    }
  };

  const handleDeleteAvatar = () => {
    Alert.alert(
      'Remove Photo',
      'Are you sure you want to remove your profile picture?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteAvatar.mutateAsync();
              setAvatarUri(null);
              Alert.alert('Success', 'Profile picture removed');
            } catch (error: any) {
              Alert.alert('Error', error.message || 'Failed to remove profile picture');
            }
          },
        },
      ]
    );
  };

  const handleSave = async () => {
    try {
      // Save user contact info if changed
      const userUpdates: { full_name?: string; phone?: string } = {};
      if (fullName !== (user?.full_name || '')) {
        userUpdates.full_name = fullName || undefined;
      }
      // Strip formatting from phone before comparing/saving (store raw digits)
      const rawPhone = phone.replace(/\D/g, '');
      const existingRawPhone = (user?.phone || '').replace(/\D/g, '');
      if (rawPhone !== existingRawPhone) {
        userUpdates.phone = rawPhone || undefined;
      }

      if (Object.keys(userUpdates).length > 0) {
        await updateUser.mutateAsync(userUpdates);
      }

      // Save profile/preferences
      await updateProfile.mutateAsync({
        profession: profession || undefined,
        skills,
        experience_years: experienceYears ? parseInt(experienceYears, 10) : undefined,
        min_rate_usd: minRate ? parseFloat(minRate) : undefined,
        preferences: {
          ...profile?.preferences,
          remote_only: remoteOnly,
        },
      });

      Alert.alert('Success', 'Profile updated successfully', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to update profile');
    }
  };

  const isSaving = updateProfile.isPending || updateUser.isPending || uploadAvatar.isPending;

  if (isLoadingProfile) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Loading profile...</Text>
      </View>
    );
  }

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Edit Profile',
          headerBackTitle: 'Profile',
        }}
      />
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        <ScrollView style={styles.scrollView}>
          {/* Personal Info Section */}
          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Personal Info
            </Text>

            {/* Avatar */}
            <View style={styles.avatarContainer}>
              <TouchableOpacity onPress={pickImage} disabled={uploadAvatar.isPending}>
                {avatarUri ? (
                  <Image source={{ uri: avatarUri }} style={styles.avatar} />
                ) : (
                  <Avatar.Text
                    size={100}
                    label={user?.username?.substring(0, 2).toUpperCase() || 'U'}
                    style={styles.avatarPlaceholder}
                  />
                )}
                <View style={styles.avatarEditBadge}>
                  <IconButton
                    icon="camera"
                    size={16}
                    iconColor="#fff"
                    style={styles.avatarEditIcon}
                  />
                </View>
              </TouchableOpacity>
              {avatarUri && (
                <Button
                  mode="text"
                  onPress={handleDeleteAvatar}
                  textColor="#dc2626"
                  compact
                  style={styles.removeAvatarButton}
                >
                  Remove Photo
                </Button>
              )}
              {uploadAvatar.isPending && (
                <Text style={styles.uploadingText}>Uploading...</Text>
              )}
            </View>

            <TextInput
              label="Full Name"
              value={fullName}
              onChangeText={setFullName}
              mode="outlined"
              placeholder="Your full name"
              style={styles.input}
            />

            <TextInput
              label="Phone Number"
              value={phone}
              onChangeText={(text) => setPhone(formatPhoneNumber(text))}
              mode="outlined"
              placeholder="(555) 555-5555"
              keyboardType="phone-pad"
              style={styles.input}
            />

            <TextInput
              label="Email"
              value={user?.email || ''}
              mode="outlined"
              disabled
              style={styles.input}
            />
          </Surface>

          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Professional Info
            </Text>

            <TextInput
              label="Profession"
              value={profession}
              onChangeText={setProfession}
              mode="outlined"
              placeholder="e.g., Software Engineer, Designer"
              style={styles.input}
            />

            <TextInput
              label="Years of Experience"
              value={experienceYears}
              onChangeText={setExperienceYears}
              mode="outlined"
              keyboardType="numeric"
              placeholder="e.g., 5"
              style={styles.input}
            />
          </Surface>

          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Skills
            </Text>
            <View style={styles.skillInputRow}>
              <TextInput
                label="Add a skill"
                value={newSkill}
                onChangeText={setNewSkill}
                mode="outlined"
                placeholder="e.g., React, Python"
                style={styles.skillInput}
                onSubmitEditing={handleAddSkill}
              />
              <Button
                mode="contained"
                onPress={handleAddSkill}
                style={styles.addButton}
                compact
              >
                Add
              </Button>
            </View>
            <View style={styles.skillsContainer}>
              {skills.map((skill) => (
                <Chip
                  key={skill}
                  onClose={() => handleRemoveSkill(skill)}
                  style={styles.skillChip}
                >
                  {skill}
                </Chip>
              ))}
              {skills.length === 0 && (
                <Text style={styles.emptyText}>No skills added yet</Text>
              )}
            </View>
          </Surface>

          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Rate Preferences
            </Text>

            <TextInput
              label="Minimum Hourly Rate (USD)"
              value={minRate}
              onChangeText={setMinRate}
              mode="outlined"
              keyboardType="numeric"
              placeholder="e.g., 50"
              left={<TextInput.Affix text="$" />}
              right={<TextInput.Affix text="/hr" />}
              style={styles.input}
            />
          </Surface>

          <Surface style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Job Preferences
            </Text>

            <View style={styles.switchRow}>
              <View style={styles.switchLabel}>
                <Text variant="bodyLarge">Remote Only</Text>
                <Text variant="bodySmall" style={styles.switchDescription}>
                  Only show remote job opportunities
                </Text>
              </View>
              <Switch value={remoteOnly} onValueChange={setRemoteOnly} />
            </View>
          </Surface>

          <View style={styles.buttonContainer}>
            <Button
              mode="contained"
              onPress={handleSave}
              loading={isSaving}
              disabled={isSaving}
              style={styles.saveButton}
            >
              Save Changes
            </Button>
            <Button
              mode="outlined"
              onPress={() => router.back()}
              style={styles.cancelButton}
            >
              Cancel
            </Button>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  section: {
    margin: 16,
    marginBottom: 8,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  sectionTitle: {
    fontWeight: '600',
    marginBottom: 16,
    color: '#111827',
  },
  avatarContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
  },
  avatarPlaceholder: {
    backgroundColor: '#6366f1',
  },
  avatarEditBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    backgroundColor: '#6366f1',
    borderRadius: 16,
    width: 32,
    height: 32,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarEditIcon: {
    margin: 0,
  },
  removeAvatarButton: {
    marginTop: 8,
  },
  uploadingText: {
    marginTop: 8,
    color: '#6b7280',
    fontSize: 12,
  },
  input: {
    marginBottom: 12,
    backgroundColor: '#fff',
  },
  skillInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  skillInput: {
    flex: 1,
    backgroundColor: '#fff',
  },
  addButton: {
    marginTop: 6,
  },
  skillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    backgroundColor: '#e0e7ff',
  },
  emptyText: {
    color: '#9ca3af',
    fontStyle: 'italic',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  switchLabel: {
    flex: 1,
    marginRight: 16,
  },
  switchDescription: {
    color: '#6b7280',
    marginTop: 2,
  },
  buttonContainer: {
    padding: 16,
    paddingBottom: 32,
    gap: 12,
  },
  saveButton: {
    paddingVertical: 4,
  },
  cancelButton: {
    paddingVertical: 4,
  },
});
