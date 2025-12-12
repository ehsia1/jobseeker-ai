import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from 'react-native-paper';

interface ScoreBadgeProps {
  score: number;
  size?: 'small' | 'medium' | 'large';
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e'; // green
  if (score >= 60) return '#3b82f6'; // blue
  if (score >= 40) return '#eab308'; // yellow
  return '#6b7280'; // gray
}

function getScoreLabel(score: number): string {
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Good';
  if (score >= 40) return 'Fair';
  return 'Low';
}

export function ScoreBadge({ score, size = 'medium' }: ScoreBadgeProps) {
  const dimensions = {
    small: { width: 32, height: 32, fontSize: 12 },
    medium: { width: 44, height: 44, fontSize: 16 },
    large: { width: 64, height: 64, fontSize: 24 },
  }[size];

  return (
    <View
      style={[
        styles.badge,
        {
          width: dimensions.width,
          height: dimensions.height,
          borderRadius: dimensions.width / 2,
          backgroundColor: getScoreColor(score),
        },
      ]}
    >
      <Text
        style={[styles.score, { fontSize: dimensions.fontSize }]}
      >
        {Math.round(score)}
      </Text>
    </View>
  );
}

export function ScoreBreakdownBar({
  label,
  score,
  maxScore = 100,
}: {
  label: string;
  score: number;
  maxScore?: number;
}) {
  const percentage = (score / maxScore) * 100;
  const color = getScoreColor(score);

  return (
    <View style={styles.breakdownRow}>
      <Text style={styles.breakdownLabel}>{label}</Text>
      <View style={styles.barContainer}>
        <View
          style={[
            styles.bar,
            { width: `${percentage}%`, backgroundColor: color },
          ]}
        />
      </View>
      <Text style={styles.breakdownScore}>{Math.round(score)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  score: {
    color: '#fff',
    fontWeight: '700',
  },
  breakdownRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 4,
  },
  breakdownLabel: {
    width: 120,
    fontSize: 14,
    color: '#4b5563',
  },
  barContainer: {
    flex: 1,
    height: 8,
    backgroundColor: '#e5e7eb',
    borderRadius: 4,
    marginHorizontal: 8,
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    borderRadius: 4,
  },
  breakdownScore: {
    width: 32,
    textAlign: 'right',
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
});
