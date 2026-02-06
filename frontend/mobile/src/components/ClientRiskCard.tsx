import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  Pressable,
  ScrollView,
} from 'react-native';
import {
  Text,
  Button,
  Chip,
  Surface,
  ActivityIndicator,
  ProgressBar,
} from 'react-native-paper';
import { Ionicons } from '@expo/vector-icons';
import { useJobRisk, useAnalyzeJobRisk } from '../hooks/useJobs';
import type { ClientRiskAssessment, RiskLevel, RedFlag, GreenFlag } from '@jobseeker/shared';

interface ClientRiskCardProps {
  jobId: string;
  compact?: boolean;
  showAnalyzeButton?: boolean;
  onAnalyzeComplete?: (assessment: ClientRiskAssessment) => void;
}

const RISK_COLORS: Record<RiskLevel, { bg: string; text: string; border: string }> = {
  low: { bg: '#dcfce7', text: '#15803d', border: '#86efac' },
  medium: { bg: '#fef9c3', text: '#a16207', border: '#fde047' },
  high: { bg: '#fed7aa', text: '#c2410c', border: '#fdba74' },
  critical: { bg: '#fecaca', text: '#b91c1c', border: '#fca5a5' },
};

const RISK_ICONS: Record<RiskLevel, string> = {
  low: 'shield-checkmark',
  medium: 'warning-outline',
  high: 'alert-circle-outline',
  critical: 'alert',
};

export function ClientRiskCard({
  jobId,
  compact = false,
  showAnalyzeButton = true,
  onAnalyzeComplete,
}: ClientRiskCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { data: assessment, isLoading, isError } = useJobRisk(jobId, false);
  const analyzeMutation = useAnalyzeJobRisk();

  const handleAnalyze = async () => {
    try {
      const result = await analyzeMutation.mutateAsync({ jobId });
      onAnalyzeComplete?.(result);
    } catch (error) {
      console.error('Failed to analyze job risk:', error);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <Surface style={styles.card}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color="#6b7280" />
          <Text style={styles.loadingText}>Loading risk assessment...</Text>
        </View>
      </Surface>
    );
  }

  // No assessment - show analyze button
  if (!assessment) {
    if (!showAnalyzeButton) {
      return null;
    }

    return (
      <Surface style={styles.card}>
        <View style={styles.noAssessmentContainer}>
          <Ionicons name="shield-outline" size={24} color="#6b7280" />
          <Text style={styles.noAssessmentText}>No risk assessment available</Text>
          <Button
            mode="outlined"
            onPress={handleAnalyze}
            loading={analyzeMutation.isPending}
            disabled={analyzeMutation.isPending}
            compact
          >
            Analyze Risk
          </Button>
        </View>
      </Surface>
    );
  }

  const riskColors = RISK_COLORS[assessment.risk_level];
  const riskIcon = RISK_ICONS[assessment.risk_level];

  // Compact view
  if (compact) {
    return (
      <Pressable onPress={() => setExpanded(!expanded)}>
        <Surface style={[styles.compactCard, { borderColor: riskColors.border }]}>
          <View style={styles.compactHeader}>
            <View style={[styles.riskBadge, { backgroundColor: riskColors.bg }]}>
              <Ionicons name={riskIcon as any} size={16} color={riskColors.text} />
              <Text style={[styles.riskScore, { color: riskColors.text }]}>
                {assessment.risk_score}
              </Text>
            </View>
            <Text style={styles.compactLabel}>
              {assessment.risk_level.charAt(0).toUpperCase() + assessment.risk_level.slice(1)} Risk
            </Text>
            <Ionicons
              name={expanded ? 'chevron-up' : 'chevron-down'}
              size={16}
              color="#6b7280"
            />
          </View>

          {expanded && (
            <View style={styles.compactExpanded}>
              {assessment.summary && (
                <Text style={styles.summary}>{assessment.summary}</Text>
              )}
              {assessment.red_flags.length > 0 && (
                <View style={styles.flagsRow}>
                  {assessment.red_flags.slice(0, 2).map((flag, idx) => (
                    <Chip
                      key={idx}
                      style={styles.redFlagChip}
                      textStyle={styles.flagChipText}
                      compact
                    >
                      {flag.flag}
                    </Chip>
                  ))}
                </View>
              )}
            </View>
          )}
        </Surface>
      </Pressable>
    );
  }

  // Full view
  return (
    <Surface style={styles.card}>
      {/* Header */}
      <View style={styles.header}>
        <View style={[styles.riskScoreCircle, { backgroundColor: riskColors.bg }]}>
          <Text style={[styles.riskScoreNumber, { color: riskColors.text }]}>
            {assessment.risk_score}
          </Text>
          <Text style={[styles.riskScoreLabel, { color: riskColors.text }]}>
            Risk
          </Text>
        </View>
        <View style={styles.headerText}>
          <View style={styles.riskLevelRow}>
            <Ionicons name={riskIcon as any} size={20} color={riskColors.text} />
            <Text style={[styles.riskLevelText, { color: riskColors.text }]}>
              {assessment.risk_level.charAt(0).toUpperCase() + assessment.risk_level.slice(1)} Risk
            </Text>
          </View>
          {assessment.summary && (
            <Text style={styles.summary} numberOfLines={2}>
              {assessment.summary}
            </Text>
          )}
        </View>
      </View>

      {/* Risk Breakdown */}
      <View style={styles.breakdownSection}>
        <Text style={styles.sectionTitle}>Risk Breakdown</Text>
        <View style={styles.breakdownBars}>
          {Object.entries(assessment.risk_breakdown || {}).map(([category, data]) => (
            <View key={category} style={styles.breakdownItem}>
              <View style={styles.breakdownLabel}>
                <Text style={styles.categoryName}>
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                </Text>
                <Text style={styles.categoryScore}>{data.score}%</Text>
              </View>
              <ProgressBar
                progress={data.score / 100}
                color={data.score >= 50 ? '#f59e0b' : data.score >= 25 ? '#eab308' : '#22c55e'}
                style={styles.progressBar}
              />
            </View>
          ))}
        </View>
      </View>

      {/* Red Flags */}
      {assessment.red_flags.length > 0 && (
        <View style={styles.flagsSection}>
          <Text style={styles.sectionTitle}>Concerns ({assessment.red_flags.length})</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.flagsScroll}
          >
            {assessment.red_flags.map((flag, idx) => (
              <View key={idx} style={styles.flagCard}>
                <View style={[styles.severityBadge, { backgroundColor: getSeverityColor(flag.severity) }]}>
                  <Text style={styles.severityText}>{flag.severity}</Text>
                </View>
                <Text style={styles.flagText}>{flag.flag}</Text>
                <Text style={styles.flagCategory}>{flag.category}</Text>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Green Flags */}
      {assessment.green_flags.length > 0 && (
        <View style={styles.flagsSection}>
          <Text style={styles.sectionTitle}>Positives ({assessment.green_flags.length})</Text>
          <View style={styles.greenFlagsRow}>
            {assessment.green_flags.slice(0, 4).map((flag, idx) => (
              <Chip
                key={idx}
                style={styles.greenFlagChip}
                textStyle={styles.greenFlagText}
                icon={() => <Ionicons name="checkmark-circle" size={14} color="#15803d" />}
                compact
              >
                {flag.flag}
              </Chip>
            ))}
          </View>
        </View>
      )}

      {/* Recommendations */}
      {assessment.recommendations.length > 0 && (
        <View style={styles.recommendationsSection}>
          <Text style={styles.sectionTitle}>Recommendations</Text>
          {assessment.recommendations.slice(0, 3).map((rec, idx) => (
            <View key={idx} style={styles.recommendationItem}>
              <Ionicons name="bulb-outline" size={16} color="#3b82f6" />
              <Text style={styles.recommendationText}>{rec}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Refresh button */}
      <Button
        mode="text"
        onPress={handleAnalyze}
        loading={analyzeMutation.isPending}
        icon="refresh"
        compact
        style={styles.refreshButton}
      >
        Re-analyze
      </Button>
    </Surface>
  );
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return '#dc2626';
    case 'high':
      return '#f97316';
    case 'medium':
      return '#eab308';
    case 'low':
    default:
      return '#6b7280';
  }
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    padding: 16,
    backgroundColor: '#fff',
  },
  compactCard: {
    borderRadius: 8,
    padding: 12,
    backgroundColor: '#fff',
    borderWidth: 1,
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
  },
  loadingText: {
    color: '#6b7280',
    fontSize: 14,
  },
  noAssessmentContainer: {
    alignItems: 'center',
    gap: 8,
    padding: 16,
  },
  noAssessmentText: {
    color: '#6b7280',
    fontSize: 14,
  },
  header: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 16,
  },
  riskScoreCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  riskScoreNumber: {
    fontSize: 24,
    fontWeight: '700',
  },
  riskScoreLabel: {
    fontSize: 10,
    fontWeight: '500',
  },
  headerText: {
    flex: 1,
    justifyContent: 'center',
  },
  riskLevelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  riskLevelText: {
    fontSize: 16,
    fontWeight: '600',
  },
  summary: {
    fontSize: 13,
    color: '#6b7280',
    lineHeight: 18,
  },
  compactHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  riskBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  riskScore: {
    fontSize: 14,
    fontWeight: '600',
  },
  compactLabel: {
    flex: 1,
    fontSize: 14,
    color: '#374151',
  },
  compactExpanded: {
    marginTop: 12,
    gap: 8,
  },
  flagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
  },
  breakdownSection: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  breakdownBars: {
    gap: 8,
  },
  breakdownItem: {
    gap: 4,
  },
  breakdownLabel: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  categoryName: {
    fontSize: 12,
    color: '#6b7280',
  },
  categoryScore: {
    fontSize: 12,
    fontWeight: '500',
    color: '#374151',
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
    backgroundColor: '#e5e7eb',
  },
  flagsSection: {
    marginBottom: 16,
  },
  flagsScroll: {
    gap: 8,
  },
  flagCard: {
    backgroundColor: '#fef2f2',
    borderRadius: 8,
    padding: 10,
    width: 160,
    gap: 4,
  },
  severityBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  severityText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#fff',
    textTransform: 'uppercase',
  },
  flagText: {
    fontSize: 12,
    color: '#374151',
    fontWeight: '500',
  },
  flagCategory: {
    fontSize: 10,
    color: '#9ca3af',
    textTransform: 'capitalize',
  },
  redFlagChip: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  flagChipText: {
    fontSize: 11,
    color: '#b91c1c',
  },
  greenFlagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  greenFlagChip: {
    backgroundColor: '#f0fdf4',
    borderColor: '#86efac',
  },
  greenFlagText: {
    fontSize: 11,
    color: '#15803d',
  },
  recommendationsSection: {
    marginBottom: 12,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 6,
  },
  recommendationText: {
    flex: 1,
    fontSize: 13,
    color: '#374151',
    lineHeight: 18,
  },
  refreshButton: {
    alignSelf: 'center',
  },
});

export default ClientRiskCard;
