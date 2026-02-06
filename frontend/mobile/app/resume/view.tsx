import React from 'react';
import { View, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import {
  Text,
  Card,
  Chip,
  Divider,
  ActivityIndicator,
  IconButton,
  Surface,
} from 'react-native-paper';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useResume } from '../../src/hooks/useJobs';
import type { WorkExperience, EducationEntry } from '@jobseeker/shared';

export default function ResumeViewScreen() {
  const router = useRouter();

  // Use React Query hook - staleTime: 0 ensures always fresh data
  const {
    data: resume,
    isLoading,
    error: queryError,
    refetch,
    isRefetching,
  } = useResume();

  const error = queryError ? (queryError as Error).message : null;

  const onRefresh = () => {
    refetch();
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Present';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  const formatDuration = (exp: WorkExperience) => {
    if (exp.duration_text) return exp.duration_text;
    if (exp.duration_months) {
      const years = Math.floor(exp.duration_months / 12);
      const months = exp.duration_months % 12;
      if (years > 0 && months > 0) return `${years}y ${months}mo`;
      if (years > 0) return `${years} year${years > 1 ? 's' : ''}`;
      return `${months} month${months > 1 ? 's' : ''}`;
    }
    return '';
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Stack.Screen
          options={{
            title: 'Resume',
            headerLeft: () => (
              <IconButton icon="arrow-left" onPress={() => router.back()} />
            ),
          }}
        />
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.loadingText}>Loading resume...</Text>
      </View>
    );
  }

  if (error || !resume) {
    return (
      <View style={styles.errorContainer}>
        <Stack.Screen
          options={{
            title: 'Resume',
            headerLeft: () => (
              <IconButton icon="arrow-left" onPress={() => router.back()} />
            ),
          }}
        />
        <Ionicons name="alert-circle-outline" size={64} color="#dc2626" />
        <Text style={styles.errorText}>{error || 'No resume found'}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={onRefresh} />
      }
    >
      <Stack.Screen
        options={{
          title: 'My Resume',
          headerLeft: () => (
            <IconButton icon="arrow-left" onPress={() => router.back()} />
          ),
          headerRight: () => (
            <IconButton icon="pencil" onPress={() => router.push('/resume/edit' as any)} />
          ),
        }}
      />

      {/* Header / Contact Info */}
      <Card style={styles.headerCard}>
        <View style={styles.headerContent}>
          <Text variant="headlineMedium" style={styles.name}>
            {resume.full_name || 'No Name'}
          </Text>

          {resume.summary && (
            <Text variant="bodyMedium" style={styles.summary}>
              {resume.summary}
            </Text>
          )}

          <View style={styles.contactInfo}>
            {resume.email && (
              <View style={styles.contactItem}>
                <Ionicons name="mail-outline" size={16} color="#6b7280" />
                <Text style={styles.contactText}>{resume.email}</Text>
              </View>
            )}
            {resume.phone && (
              <View style={styles.contactItem}>
                <Ionicons name="call-outline" size={16} color="#6b7280" />
                <Text style={styles.contactText}>{resume.phone}</Text>
              </View>
            )}
            {resume.location && (
              <View style={styles.contactItem}>
                <Ionicons name="location-outline" size={16} color="#6b7280" />
                <Text style={styles.contactText}>{resume.location}</Text>
              </View>
            )}
          </View>

          <View style={styles.linksRow}>
            {resume.linkedin_url && (
              <Chip icon="linkedin" style={styles.linkChip} textStyle={styles.linkChipText}>
                LinkedIn
              </Chip>
            )}
            {resume.github_url && (
              <Chip icon="github" style={styles.linkChip} textStyle={styles.linkChipText}>
                GitHub
              </Chip>
            )}
            {resume.portfolio_url && (
              <Chip icon="web" style={styles.linkChip} textStyle={styles.linkChipText}>
                Portfolio
              </Chip>
            )}
          </View>
        </View>
      </Card>

      {/* Skills */}
      {resume.skills && resume.skills.length > 0 && (
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="code-slash" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Skills
            </Text>
          </View>
          <Divider style={styles.divider} />
          <View style={styles.skillsGrid}>
            {resume.skills.map((skill: string, index: number) => (
              <Chip key={index} style={styles.skillChip} textStyle={styles.skillChipText}>
                {skill}
              </Chip>
            ))}
          </View>
        </Card>
      )}

      {/* Work Experience */}
      {resume.work_experiences && resume.work_experiences.length > 0 && (
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="briefcase-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Work Experience
            </Text>
            <Text style={styles.totalExperience}>
              {resume.total_experience_years} years total
            </Text>
          </View>
          <Divider style={styles.divider} />
          {resume.work_experiences.map((exp: WorkExperience, index: number) => (
            <View key={exp.id || index}>
              <View style={styles.experienceItem}>
                <View style={styles.experienceHeader}>
                  <Text variant="titleSmall" style={styles.jobTitle}>
                    {exp.title}
                  </Text>
                  {exp.is_current && (
                    <Chip style={styles.currentChip} textStyle={styles.currentChipText}>
                      Current
                    </Chip>
                  )}
                </View>
                <Text style={styles.company}>{exp.company}</Text>
                <View style={styles.experienceMeta}>
                  <Text style={styles.dates}>
                    {formatDate(exp.start_date)} - {formatDate(exp.end_date)}
                  </Text>
                  {formatDuration(exp) && (
                    <Text style={styles.duration}>({formatDuration(exp)})</Text>
                  )}
                </View>
                {(exp.location || exp.is_remote) && (
                  <View style={styles.locationRow}>
                    <Ionicons name="location-outline" size={14} color="#9ca3af" />
                    <Text style={styles.locationText}>
                      {exp.location || ''}{exp.is_remote ? (exp.location ? ' (Remote)' : 'Remote') : ''}
                    </Text>
                  </View>
                )}

                {exp.description && (
                  <Text style={styles.description}>{exp.description}</Text>
                )}

                {exp.achievements && exp.achievements.length > 0 && (
                  <View style={styles.achievements}>
                    {exp.achievements.map((achievement: string, i: number) => (
                      <View key={i} style={styles.achievementItem}>
                        <Text style={styles.bullet}>•</Text>
                        <Text style={styles.achievementText}>{achievement}</Text>
                      </View>
                    ))}
                  </View>
                )}

                {exp.skills_used && exp.skills_used.length > 0 && (
                  <View style={styles.usedSkills}>
                    {exp.skills_used.slice(0, 6).map((skill: string, i: number) => (
                      <Chip key={i} style={styles.usedSkillChip} textStyle={styles.usedSkillText}>
                        {skill}
                      </Chip>
                    ))}
                    {exp.skills_used.length > 6 && (
                      <Text style={styles.moreSkills}>+{exp.skills_used.length - 6} more</Text>
                    )}
                  </View>
                )}
              </View>
              {index < resume.work_experiences.length - 1 && (
                <Divider style={styles.experienceDivider} />
              )}
            </View>
          ))}
        </Card>
      )}

      {/* Education */}
      {resume.education && resume.education.length > 0 && (
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="school-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Education
            </Text>
          </View>
          <Divider style={styles.divider} />
          {resume.education.map((edu: EducationEntry, index: number) => (
            <View key={index} style={styles.educationItem}>
              <Text variant="titleSmall" style={styles.degree}>
                {edu.degree}{edu.field ? ` in ${edu.field}` : ''}
              </Text>
              <Text style={styles.school}>{edu.school}</Text>
              <View style={styles.eduMeta}>
                {edu.year && <Text style={styles.year}>{edu.year}</Text>}
                {edu.gpa && <Text style={styles.gpa}>GPA: {edu.gpa}</Text>}
              </View>
            </View>
          ))}
        </Card>
      )}

      {/* Certifications */}
      {resume.certifications && resume.certifications.length > 0 && (
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="ribbon-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Certifications
            </Text>
          </View>
          <Divider style={styles.divider} />
          <View style={styles.certList}>
            {resume.certifications.map((cert: string, index: number) => (
              <View key={index} style={styles.certItem}>
                <Ionicons name="checkmark-circle" size={16} color="#10b981" />
                <Text style={styles.certText}>{cert}</Text>
              </View>
            ))}
          </View>
        </Card>
      )}

      {/* Languages */}
      {resume.languages && resume.languages.length > 0 && (
        <Card style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Ionicons name="language-outline" size={20} color="#3b82f6" />
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Languages
            </Text>
          </View>
          <Divider style={styles.divider} />
          <View style={styles.languagesRow}>
            {resume.languages.map((lang: string, index: number) => (
              <Chip key={index} style={styles.languageChip}>
                {lang}
              </Chip>
            ))}
          </View>
        </Card>
      )}

      {/* Parse Quality */}
      {resume.parse_quality_score !== undefined && (
        <Surface style={styles.qualityBadge} elevation={1}>
          <Text style={styles.qualityText}>
            Parse Quality: {resume.parse_quality_score}%
          </Text>
          {resume.parsed_at && (
            <Text style={styles.parsedAt}>
              Parsed {new Date(resume.parsed_at).toLocaleDateString()}
            </Text>
          )}
        </Surface>
      )}

      <View style={styles.bottomPadding} />
    </ScrollView>
  );
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
  headerCard: {
    margin: 16,
    marginBottom: 8,
  },
  headerContent: {
    padding: 20,
  },
  name: {
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  summary: {
    color: '#4b5563',
    lineHeight: 22,
    marginBottom: 16,
  },
  contactInfo: {
    marginBottom: 12,
  },
  contactItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  contactText: {
    marginLeft: 8,
    color: '#4b5563',
    fontSize: 14,
  },
  linksRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  linkChip: {
    backgroundColor: '#dbeafe',
  },
  linkChipText: {
    color: '#1d4ed8',
    fontSize: 12,
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
  totalExperience: {
    fontSize: 12,
    color: '#6b7280',
  },
  divider: {
    marginBottom: 16,
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
  experienceItem: {
    paddingVertical: 8,
  },
  experienceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  jobTitle: {
    fontWeight: '600',
    color: '#111827',
    flex: 1,
  },
  currentChip: {
    backgroundColor: '#dcfce7',
    height: 24,
  },
  currentChipText: {
    color: '#166534',
    fontSize: 11,
  },
  company: {
    color: '#3b82f6',
    fontWeight: '500',
    marginTop: 2,
  },
  experienceMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  dates: {
    color: '#6b7280',
    fontSize: 13,
  },
  duration: {
    color: '#9ca3af',
    fontSize: 13,
    marginLeft: 8,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  locationText: {
    color: '#9ca3af',
    fontSize: 13,
    marginLeft: 4,
  },
  description: {
    color: '#4b5563',
    marginTop: 10,
    lineHeight: 20,
  },
  achievements: {
    marginTop: 10,
  },
  achievementItem: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  bullet: {
    color: '#3b82f6',
    marginRight: 8,
    fontWeight: '600',
  },
  achievementText: {
    flex: 1,
    color: '#374151',
    lineHeight: 20,
  },
  usedSkills: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 10,
    gap: 6,
    alignItems: 'center',
  },
  usedSkillChip: {
    backgroundColor: '#f3f4f6',
    height: 26,
  },
  usedSkillText: {
    color: '#6b7280',
    fontSize: 11,
  },
  moreSkills: {
    color: '#9ca3af',
    fontSize: 12,
  },
  experienceDivider: {
    marginVertical: 12,
  },
  educationItem: {
    marginBottom: 12,
  },
  degree: {
    fontWeight: '600',
    color: '#111827',
  },
  school: {
    color: '#3b82f6',
    marginTop: 2,
  },
  eduMeta: {
    flexDirection: 'row',
    marginTop: 4,
    gap: 16,
  },
  year: {
    color: '#6b7280',
    fontSize: 13,
  },
  gpa: {
    color: '#6b7280',
    fontSize: 13,
  },
  certList: {
    gap: 8,
  },
  certItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  certText: {
    marginLeft: 8,
    color: '#374151',
    flex: 1,
  },
  languagesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  languageChip: {
    backgroundColor: '#fef3c7',
  },
  qualityBadge: {
    marginHorizontal: 16,
    marginVertical: 8,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#fff',
    alignItems: 'center',
  },
  qualityText: {
    color: '#6b7280',
    fontSize: 13,
  },
  parsedAt: {
    color: '#9ca3af',
    fontSize: 12,
    marginTop: 4,
  },
  bottomPadding: {
    height: 32,
  },
});
