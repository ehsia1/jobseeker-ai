import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {
  Text,
  TextInput,
  Button,
  Chip,
  Switch,
  Surface,
  Divider,
} from 'react-native-paper';
import { useRouter, Stack } from 'expo-router';
import { useProfile, useUpdateProfile } from '../../src/hooks/useJobs';

export default function EditProfileScreen() {
  const router = useRouter();
  const { data: profile, isLoading: isLoadingProfile } = useProfile();
  const updateProfile = useUpdateProfile();

  // Form state
  const [profession, setProfession] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState('');
  const [experienceYears, setExperienceYears] = useState('');
  const [minRate, setMinRate] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);

  // Populate form with existing profile data
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

  const handleSave = async () => {
    try {
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
              loading={updateProfile.isPending}
              disabled={updateProfile.isPending}
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
