import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { Text, Card, Button, Chip, ProgressBar } from 'react-native-paper';
import { Stack, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useSubscription } from '../../src/hooks/useJobs';

const tierColors: Record<string, string> = {
  free: '#6b7280',
  starter: '#3b82f6',
  pro: '#8b5cf6',
  power: '#f59e0b',
};

const tierNames: Record<string, string> = {
  free: 'Free',
  starter: 'Starter',
  pro: 'Professional',
  power: 'Power User',
};

export default function SubscriptionScreen() {
  const router = useRouter();
  const { data: subscription, isLoading } = useSubscription();

  const tier = subscription?.tier || 'free';
  const isActive = subscription?.has_active_subscription ?? subscription?.is_active;

  return (
    <>
      <Stack.Screen
        options={{
          headerTitle: 'Subscription',
          presentation: 'modal',
        }}
      />
      <ScrollView style={styles.container}>
        {/* Current Plan Card */}
        <Card style={styles.planCard}>
          <Card.Content>
            <View style={styles.planHeader}>
              <Chip
                style={[styles.tierChip, { backgroundColor: `${tierColors[tier]}20` }]}
                textStyle={[styles.tierChipText, { color: tierColors[tier] }]}
              >
                {tierNames[tier]}
              </Chip>
              {isActive && (
                <Chip style={styles.statusChip}>Active</Chip>
              )}
            </View>
            <Text variant="headlineMedium" style={styles.planTitle}>
              Your Current Plan
            </Text>
            <Text variant="bodyMedium" style={styles.planDescription}>
              {tier === 'free'
                ? 'Basic features to get started with your job search.'
                : `Enjoy ${tierNames[tier]} features for your job search.`}
            </Text>
          </Card.Content>
        </Card>

        {/* Usage Stats */}
        {subscription && (
          <Card style={styles.usageCard}>
            <Card.Content>
              <Text variant="titleMedium" style={styles.sectionTitle}>
                Usage Stats
              </Text>

              <View style={styles.usageItem}>
                <View style={styles.usageHeader}>
                  <Ionicons name="search" size={20} color="#3b82f6" />
                  <Text variant="bodyMedium" style={styles.usageLabel}>
                    Searches Today
                  </Text>
                  <Text variant="bodySmall" style={styles.usageCount}>
                    {subscription.searches_remaining_today} remaining
                  </Text>
                </View>
              </View>

              <View style={styles.usageItem}>
                <View style={styles.usageHeader}>
                  <Ionicons name="document-text" size={20} color="#8b5cf6" />
                  <Text variant="bodyMedium" style={styles.usageLabel}>
                    Cover Letters
                  </Text>
                  <Text variant="bodySmall" style={styles.usageCount}>
                    {subscription.proposals_remaining} remaining
                  </Text>
                </View>
              </View>

              <View style={styles.usageItem}>
                <View style={styles.usageHeader}>
                  <Ionicons name="reader" size={20} color="#10b981" />
                  <Text variant="bodyMedium" style={styles.usageLabel}>
                    JD Parses
                  </Text>
                  <Text variant="bodySmall" style={styles.usageCount}>
                    {subscription.jd_parses_remaining} remaining
                  </Text>
                </View>
              </View>
            </Card.Content>
          </Card>
        )}

        {/* Upgrade Section */}
        {tier === 'free' && (
          <Card style={styles.upgradeCard}>
            <Card.Content>
              <Text variant="titleMedium" style={styles.sectionTitle}>
                Upgrade Your Plan
              </Text>
              <Text variant="bodyMedium" style={styles.upgradeDescription}>
                Get unlimited AI-powered job matches, cover letters, and more with a premium plan.
              </Text>
              <Button
                mode="contained"
                onPress={() => {/* TODO: Implement upgrade flow */}}
                style={styles.upgradeButton}
              >
                View Plans
              </Button>
            </Card.Content>
          </Card>
        )}

        {/* Back Button */}
        <Button
          mode="outlined"
          onPress={() => router.back()}
          style={styles.backButton}
        >
          Go Back
        </Button>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
    padding: 16,
  },
  planCard: {
    marginBottom: 16,
    backgroundColor: '#fff',
  },
  planHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  tierChip: {
    height: 28,
  },
  tierChipText: {
    fontWeight: '600',
  },
  statusChip: {
    height: 24,
    backgroundColor: '#dcfce7',
  },
  planTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 8,
  },
  planDescription: {
    color: '#6b7280',
  },
  usageCard: {
    marginBottom: 16,
    backgroundColor: '#fff',
  },
  sectionTitle: {
    color: '#111827',
    fontWeight: '600',
    marginBottom: 16,
  },
  usageItem: {
    marginBottom: 16,
  },
  usageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  usageLabel: {
    flex: 1,
    color: '#374151',
  },
  usageCount: {
    color: '#6b7280',
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
  },
  upgradeCard: {
    marginBottom: 16,
    backgroundColor: '#fff',
    borderColor: '#3b82f6',
    borderWidth: 1,
  },
  upgradeDescription: {
    color: '#6b7280',
    marginBottom: 16,
  },
  upgradeButton: {
    backgroundColor: '#3b82f6',
  },
  backButton: {
    marginBottom: 32,
  },
});
