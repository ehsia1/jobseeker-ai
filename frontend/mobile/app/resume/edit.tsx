import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import {
  Text,
  Card,
  Button,
  TextInput,
  Chip,
  Divider,
  ActivityIndicator,
  IconButton,
} from 'react-native-paper';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useResume, useUpdateResume } from '../../src/hooks/useJobs';

export default function ResumeEditScreen() {
  const router = useRouter();
  const { data: resume, isLoading } = useResume();
  const updateResume = useUpdateResume();

  // Form state
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('');
  const [summary, setSummary] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [portfolioUrl, setPortfolioUrl] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState('');

  // Initialize form with resume data
  useEffect(() => {
    if (resume) {
      setFullName(resume.full_name || '');
      setEmail(resume.email || '');
      setPhone(resume.phone || '');
      setLocation(resume.location || '');
      setSummary(resume.summary || '');
      setLinkedinUrl(resume.linkedin_url || '');
      setGithubUrl(resume.github_url || '');
      setPortfolioUrl(resume.portfolio_url || '');
      setSkills(resume.skills || []);
    }
  }, [resume]);

  const handleAddSkill = () => {
    const trimmedSkill = newSkill.trim();
    if (trimmedSkill && !skills.includes(trimmedSkill)) {
      setSkills([...skills, trimmedSkill]);
      setNewSkill('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter(skill => skill !== skillToRemove));
  };

  const handleSave = async () => {
    try {
      await updateResume.mutateAsync({
        full_name: fullName || undefined,
        email: email || undefined,
        phone: phone || undefined,
        location: location || undefined,
        summary: summary || undefined,
        linkedin_url: linkedinUrl || undefined,
        github_url: githubUrl || undefined,
        portfolio_url: portfolioUrl || undefined,
        skills: skills.length > 0 ? skills : undefined,
      });

      Alert.alert('Success', 'Resume updated successfully!', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to update resume');
    }
  };

  const hasChanges = () => {
    if (!resume) return false;
    return (
      fullName !== (resume.full_name || '') ||
      email !== (resume.email || '') ||
      phone !== (resume.phone || '') ||
      location !== (resume.location || '') ||
      summary !== (resume.summary || '') ||
      linkedinUrl !== (resume.linkedin_url || '') ||
      githubUrl !== (resume.github_url || '') ||
      portfolioUrl !== (resume.portfolio_url || '') ||
      JSON.stringify(skills) !== JSON.stringify(resume.skills || [])
    );
  };

  const handleBack = () => {
    if (hasChanges()) {
      Alert.alert(
        'Unsaved Changes',
        'You have unsaved changes. Are you sure you want to leave?',
        [
          { text: 'Stay', style: 'cancel' },
          { text: 'Leave', style: 'destructive', onPress: () => router.back() },
        ]
      );
    } else {
      router.back();
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Stack.Screen
          options={{
            title: 'Edit Resume',
            headerLeft: () => (
              <IconButton icon="arrow-left" onPress={handleBack} />
            ),
          }}
        />
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.loadingText}>Loading resume...</Text>
      </View>
    );
  }

  if (!resume) {
    return (
      <View style={styles.errorContainer}>
        <Stack.Screen
          options={{
            title: 'Edit Resume',
            headerLeft: () => (
              <IconButton icon="arrow-left" onPress={() => router.back()} />
            ),
          }}
        />
        <Ionicons name="alert-circle-outline" size={64} color="#dc2626" />
        <Text style={styles.errorText}>No resume found. Please upload a resume first.</Text>
        <Button mode="contained" onPress={() => router.back()} style={styles.backButton}>
          Go Back
        </Button>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Stack.Screen
        options={{
          title: 'Edit Resume',
          headerLeft: () => (
            <IconButton icon="arrow-left" onPress={handleBack} />
          ),
          headerRight: () => (
            <Button
              mode="text"
              onPress={handleSave}
              loading={updateResume.isPending}
              disabled={!hasChanges() || updateResume.isPending}
            >
              Save
            </Button>
          ),
        }}
      />

      <ScrollView style={styles.scrollView}>
        {/* Contact Information */}
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="person-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Contact Information
            </Text>
          </View>
          <Divider style={styles.divider} />

          <TextInput
            label="Full Name"
            value={fullName}
            onChangeText={setFullName}
            style={styles.input}
            mode="outlined"
          />

          <TextInput
            label="Email"
            value={email}
            onChangeText={setEmail}
            style={styles.input}
            mode="outlined"
            keyboardType="email-address"
            autoCapitalize="none"
          />

          <TextInput
            label="Phone"
            value={phone}
            onChangeText={setPhone}
            style={styles.input}
            mode="outlined"
            keyboardType="phone-pad"
          />

          <TextInput
            label="Location"
            value={location}
            onChangeText={setLocation}
            style={styles.input}
            mode="outlined"
            placeholder="City, State or Country"
          />
        </Card>

        {/* Profile Links */}
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="link-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Profile Links
            </Text>
          </View>
          <Divider style={styles.divider} />

          <TextInput
            label="LinkedIn URL"
            value={linkedinUrl}
            onChangeText={setLinkedinUrl}
            style={styles.input}
            mode="outlined"
            keyboardType="url"
            autoCapitalize="none"
            left={<TextInput.Icon icon="linkedin" />}
          />

          <TextInput
            label="GitHub URL"
            value={githubUrl}
            onChangeText={setGithubUrl}
            style={styles.input}
            mode="outlined"
            keyboardType="url"
            autoCapitalize="none"
            left={<TextInput.Icon icon="github" />}
          />

          <TextInput
            label="Portfolio URL"
            value={portfolioUrl}
            onChangeText={setPortfolioUrl}
            style={styles.input}
            mode="outlined"
            keyboardType="url"
            autoCapitalize="none"
            left={<TextInput.Icon icon="web" />}
          />
        </Card>

        {/* Summary */}
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="document-text-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Professional Summary
            </Text>
          </View>
          <Divider style={styles.divider} />

          <TextInput
            label="Summary"
            value={summary}
            onChangeText={setSummary}
            style={styles.input}
            mode="outlined"
            multiline
            numberOfLines={4}
            placeholder="Brief overview of your experience and expertise..."
          />
        </Card>

        {/* Skills */}
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="code-slash" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Skills
            </Text>
            <Text style={styles.skillCount}>{skills.length} skills</Text>
          </View>
          <Divider style={styles.divider} />

          <View style={styles.addSkillRow}>
            <TextInput
              label="Add Skill"
              value={newSkill}
              onChangeText={setNewSkill}
              style={styles.skillInput}
              mode="outlined"
              onSubmitEditing={handleAddSkill}
              returnKeyType="done"
            />
            <Button
              mode="contained"
              onPress={handleAddSkill}
              disabled={!newSkill.trim()}
              style={styles.addButton}
            >
              Add
            </Button>
          </View>

          <View style={styles.skillsGrid}>
            {skills.map((skill, index) => (
              <Chip
                key={index}
                style={styles.skillChip}
                textStyle={styles.skillChipText}
                onClose={() => handleRemoveSkill(skill)}
              >
                {skill}
              </Chip>
            ))}
          </View>

          {skills.length === 0 && (
            <Text style={styles.emptyText}>No skills added yet. Add your key skills above.</Text>
          )}
        </Card>

        {/* Info Notice */}
        <View style={styles.infoNotice}>
          <Ionicons name="information-circle-outline" size={20} color="#3b82f6" />
          <Text style={styles.infoText}>
            Work experience and education can only be updated by uploading a new resume or pasting your resume text.
          </Text>
        </View>

        {/* Save Button */}
        <Button
          mode="contained"
          onPress={handleSave}
          loading={updateResume.isPending}
          disabled={!hasChanges() || updateResume.isPending}
          style={styles.saveButton}
          icon="content-save"
        >
          Save Changes
        </Button>

        <View style={styles.bottomPadding} />
      </ScrollView>
    </KeyboardAvoidingView>
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
    backgroundColor: '#f3f4f6',
  },
  loadingText: {
    marginTop: 12,
    color: '#6b7280',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f3f4f6',
    padding: 24,
  },
  errorText: {
    marginTop: 16,
    color: '#dc2626',
    textAlign: 'center',
  },
  backButton: {
    marginTop: 16,
  },
  sectionCard: {
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  sectionTitle: {
    fontWeight: '600',
    color: '#111827',
    marginLeft: 8,
    flex: 1,
  },
  divider: {
    marginBottom: 16,
  },
  input: {
    marginBottom: 12,
    backgroundColor: '#fff',
  },
  addSkillRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 8,
  },
  skillInput: {
    flex: 1,
    backgroundColor: '#fff',
  },
  addButton: {
    marginTop: 6,
  },
  skillsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    backgroundColor: '#e0e7ff',
  },
  skillChipText: {
    color: '#4338ca',
    fontSize: 13,
  },
  skillCount: {
    fontSize: 12,
    color: '#6b7280',
  },
  emptyText: {
    color: '#9ca3af',
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 12,
  },
  infoNotice: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 12,
    backgroundColor: '#eff6ff',
    borderRadius: 8,
    gap: 8,
  },
  infoText: {
    flex: 1,
    color: '#1e40af',
    fontSize: 13,
    lineHeight: 18,
  },
  saveButton: {
    marginHorizontal: 16,
    marginTop: 8,
  },
  bottomPadding: {
    height: 32,
  },
});
