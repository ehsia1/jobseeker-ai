import React from 'react';
import { View, StyleSheet, Pressable } from 'react-native';
import { Card, Text, Chip, Badge } from 'react-native-paper';
import { Ionicons } from '@expo/vector-icons';
import type { Job, ScoredJob } from '@jobseeker/shared';

interface JobCardProps {
  job: Job | ScoredJob;
  onPress?: (job: Job | ScoredJob) => void;
  onSave?: (job: Job | ScoredJob) => void;
  onApply?: (job: Job | ScoredJob) => void;
  compact?: boolean;
  isSaved?: boolean;
}

function isScoredJob(job: Job | ScoredJob): job is ScoredJob {
  return 'total_score' in job;
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e'; // green
  if (score >= 60) return '#3b82f6'; // blue
  if (score >= 40) return '#eab308'; // yellow
  return '#6b7280'; // gray
}

function formatRate(min?: number, max?: number, type?: string): string {
  if (!min && !max) return '';
  const rateType = type === 'hourly' ? '/hr' : type === 'fixed' ? ' fixed' : '';
  if (min && max) return `$${min}-$${max}${rateType}`;
  if (min) return `$${min}+${rateType}`;
  return `Up to $${max}${rateType}`;
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function JobCard({ job, onPress, onSave, onApply, compact = false, isSaved = false }: JobCardProps) {
  const scored = isScoredJob(job);
  const rate = formatRate(job.rate_min, job.rate_max, job.rate_type);

  const handlePress = () => onPress?.(job);
  const handleSave = () => onSave?.(job);
  const handleApply = () => onApply?.(job);

  return (
    <Card style={[styles.card, compact && styles.cardCompact]} onPress={handlePress}>
      <Card.Content>
        {/* Header with score */}
        <View style={styles.header}>
          <View style={styles.titleContainer}>
            <Text variant="titleMedium" numberOfLines={2} style={styles.title}>
              {job.title}
            </Text>
            <Text variant="bodyMedium" style={styles.company}>
              {job.company}
            </Text>
          </View>
          {scored && (
            <View
              style={[
                styles.scoreBadge,
                { backgroundColor: getScoreColor(job.total_score) },
              ]}
            >
              <Text style={styles.scoreText}>{Math.round(job.total_score)}</Text>
            </View>
          )}
        </View>

        {/* Tags row */}
        <View style={styles.tags}>
          {job.remote && (
            <Chip icon="wifi" compact style={styles.chip} textStyle={styles.chipText}>
              Remote
            </Chip>
          )}
          {job.location && !job.remote && (
            <Chip icon="map-marker" compact style={styles.chip} textStyle={styles.chipText}>
              {job.location}
            </Chip>
          )}
          {rate && (
            <Chip icon="currency-usd" compact style={styles.chip} textStyle={styles.chipText}>
              {rate}
            </Chip>
          )}
          {job.hours_per_week && (
            <Chip icon="clock-outline" compact style={styles.chip} textStyle={styles.chipText}>
              {job.hours_per_week}h/wk
            </Chip>
          )}
        </View>

        {/* Skills preview */}
        {!compact && job.skills && job.skills.length > 0 && (
          <View style={styles.skills}>
            {job.skills.slice(0, 4).map((skill, index) => (
              <Text key={index} style={styles.skill}>
                {skill}
              </Text>
            ))}
            {job.skills.length > 4 && (
              <Text style={styles.moreSkills}>+{job.skills.length - 4}</Text>
            )}
          </View>
        )}

        {/* Why this matches - brief explanation for scored jobs */}
        {!compact && scored && job.explanation && (
          <View style={styles.explanationPreview}>
            <Ionicons name="sparkles" size={12} color="#8b5cf6" />
            <Text variant="bodySmall" style={styles.explanationText} numberOfLines={2}>
              {job.explanation}
            </Text>
          </View>
        )}

        {/* Footer */}
        {!compact && (
          <View style={styles.footer}>
            <Text variant="bodySmall" style={styles.timestamp}>
              {formatTimeAgo(job.posted_at)}
            </Text>
            <View style={styles.actions}>
              {onSave && (
                <Pressable onPress={handleSave} style={styles.actionButton}>
                  <Ionicons
                    name={isSaved ? 'bookmark' : 'bookmark-outline'}
                    size={20}
                    color={isSaved ? '#3b82f6' : '#6b7280'}
                  />
                </Pressable>
              )}
              {onApply && (
                <Pressable onPress={handleApply} style={styles.actionButton}>
                  <Ionicons name="send-outline" size={20} color="#3b82f6" />
                </Pressable>
              )}
            </View>
          </View>
        )}
      </Card.Content>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    marginBottom: 12,
    backgroundColor: '#fff',
  },
  cardCompact: {
    marginBottom: 0,
    borderRadius: 0,
    elevation: 0,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  titleContainer: {
    flex: 1,
    marginRight: 12,
  },
  title: {
    fontWeight: '600',
    color: '#111827',
  },
  company: {
    color: '#6b7280',
    marginTop: 2,
  },
  scoreBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scoreText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8,
  },
  chip: {
    backgroundColor: '#f3f4f6',
    height: 28,
  },
  chipText: {
    fontSize: 12,
  },
  skills: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 12,
  },
  skill: {
    fontSize: 12,
    color: '#4b5563',
    backgroundColor: '#e5e7eb',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  moreSkills: {
    fontSize: 12,
    color: '#6b7280',
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
    paddingTop: 8,
    marginTop: 4,
  },
  timestamp: {
    color: '#9ca3af',
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    padding: 4,
  },
  explanationPreview: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginBottom: 12,
    paddingHorizontal: 8,
    paddingVertical: 6,
    backgroundColor: '#f5f3ff',
    borderRadius: 6,
  },
  explanationText: {
    flex: 1,
    color: '#6d28d9',
    fontSize: 12,
    lineHeight: 16,
  },
});
