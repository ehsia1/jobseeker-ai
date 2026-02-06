import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Pressable,
  Dimensions,
} from 'react-native';
import {
  Text,
  Button,
  Chip,
  Surface,
  ActivityIndicator,
  ProgressBar,
  SegmentedButtons,
} from 'react-native-paper';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import { useGenerateABVariants, useSelectVariant, useMarkVariantSent, useRecordOutcome } from '../hooks/useJobs';
import type { ProposalVariant, GenerateABVariantsResponse } from '@jobseeker/shared';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface ProposalABTestProps {
  jobMatchId: string;
  onClose: () => void;
  onMarkApplied: (selectedVariant: ProposalVariant) => void;
}

type ViewMode = 'side-by-side' | 'single';
type ActiveVariant = 'A' | 'B';

export function ProposalABTest({ jobMatchId, onClose, onMarkApplied }: ProposalABTestProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('side-by-side');
  const [activeVariant, setActiveVariant] = useState<ActiveVariant>('A');
  const [generatedVariants, setGeneratedVariants] = useState<GenerateABVariantsResponse | null>(null);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generateMutation = useGenerateABVariants();
  const selectMutation = useSelectVariant();
  const markSentMutation = useMarkVariantSent();

  useEffect(() => {
    // Auto-generate variants when component mounts
    handleGenerate();
  }, []);

  const handleGenerate = () => {
    generateMutation.mutate(
      {
        job_match_id: jobMatchId,
        variant_a_config: { tone: 'medium' },
        variant_b_config: { tone: 'full' },
      },
      {
        onSuccess: (data) => {
          setGeneratedVariants(data);
        },
      }
    );
  };

  const handleSelectVariant = async (variant: ProposalVariant) => {
    setSelectedVariantId(variant.id);
    await selectMutation.mutateAsync(variant.id);
  };

  const handleCopySelected = async () => {
    const selectedVariant = selectedVariantId === generatedVariants?.variant_a.id
      ? generatedVariants?.variant_a
      : generatedVariants?.variant_b;

    if (selectedVariant) {
      await Clipboard.setStringAsync(selectedVariant.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleMarkApplied = async () => {
    if (!selectedVariantId || !generatedVariants) return;

    const selectedVariant = selectedVariantId === generatedVariants.variant_a.id
      ? generatedVariants.variant_a
      : generatedVariants.variant_b;

    // Mark as sent for tracking
    await markSentMutation.mutateAsync(selectedVariantId);
    onMarkApplied(selectedVariant);
  };

  const renderVariantCard = (variant: ProposalVariant, label: string, isSelected: boolean) => {
    const isCompact = viewMode === 'side-by-side';

    return (
      <Pressable
        onPress={() => handleSelectVariant(variant)}
        style={[
          styles.variantCard,
          isCompact && styles.variantCardCompact,
          isSelected && styles.variantCardSelected,
        ]}
      >
        <View style={styles.variantHeader}>
          <View style={styles.variantLabelContainer}>
            <View style={[styles.variantBadge, label === 'A' ? styles.variantBadgeA : styles.variantBadgeB]}>
              <Text style={styles.variantBadgeText}>{label}</Text>
            </View>
            <Text style={styles.variantName}>{variant.variant_name || `Variant ${label}`}</Text>
          </View>
          {isSelected && (
            <Ionicons name="checkmark-circle" size={24} color="#10b981" />
          )}
        </View>

        <View style={styles.variantMeta}>
          {variant.tone && (
            <Chip style={styles.metaChip} textStyle={styles.metaChipText} compact>
              {variant.tone}
            </Chip>
          )}
          {variant.style && (
            <Chip style={styles.metaChip} textStyle={styles.metaChipText} compact>
              {variant.style}
            </Chip>
          )}
        </View>

        <ScrollView
          style={[styles.variantContent, isCompact && styles.variantContentCompact]}
          nestedScrollEnabled
        >
          <Text style={styles.variantText} numberOfLines={isCompact ? 15 : undefined}>
            {variant.content}
          </Text>
        </ScrollView>

        {!isCompact && (
          <Button
            mode={isSelected ? 'contained' : 'outlined'}
            onPress={() => handleSelectVariant(variant)}
            style={styles.selectButton}
            icon={isSelected ? 'check' : undefined}
          >
            {isSelected ? 'Selected' : 'Select This Version'}
          </Button>
        )}
      </Pressable>
    );
  };

  // Loading state
  if (generateMutation.isPending) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.loadingText}>Generating A/B variants...</Text>
        <Text style={styles.loadingSubtext}>
          Creating two different proposal styles for comparison
        </Text>
        <ProgressBar
          progress={0.5}
          color="#3b82f6"
          style={styles.loadingProgress}
        />
      </View>
    );
  }

  // Error state
  if (generateMutation.isError) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="warning" size={48} color="#dc2626" />
        <Text style={styles.errorText}>Failed to generate variants</Text>
        <Text style={styles.errorSubtext}>
          {generateMutation.error?.message || 'Please try again'}
        </Text>
        <Button mode="contained" onPress={handleGenerate} style={styles.retryButton}>
          Try Again
        </Button>
        <Button mode="text" onPress={onClose}>
          Cancel
        </Button>
      </View>
    );
  }

  // Results view
  if (generatedVariants) {
    return (
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Compare Proposals</Text>
            <Text style={styles.subtitle}>
              Select the version that best represents you
            </Text>
          </View>
          <Pressable onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color="#6b7280" />
          </Pressable>
        </View>

        {/* View Mode Toggle */}
        <View style={styles.viewModeContainer}>
          <SegmentedButtons
            value={viewMode}
            onValueChange={(value) => setViewMode(value as ViewMode)}
            buttons={[
              { value: 'side-by-side', label: 'Compare', icon: 'view-column' },
              { value: 'single', label: 'Full View', icon: 'view-sequential' },
            ]}
            style={styles.segmentedButtons}
          />
        </View>

        {/* Single View Tab Selector */}
        {viewMode === 'single' && (
          <View style={styles.tabContainer}>
            <Pressable
              style={[styles.tab, activeVariant === 'A' && styles.tabActive]}
              onPress={() => setActiveVariant('A')}
            >
              <Text style={[styles.tabText, activeVariant === 'A' && styles.tabTextActive]}>
                Variant A
              </Text>
            </Pressable>
            <Pressable
              style={[styles.tab, activeVariant === 'B' && styles.tabActive]}
              onPress={() => setActiveVariant('B')}
            >
              <Text style={[styles.tabText, activeVariant === 'B' && styles.tabTextActive]}>
                Variant B
              </Text>
            </Pressable>
          </View>
        )}

        {/* Variants */}
        <ScrollView
          style={styles.variantsScroll}
          horizontal={viewMode === 'side-by-side'}
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={viewMode === 'side-by-side' ? styles.sideBySideContent : undefined}
        >
          {viewMode === 'side-by-side' ? (
            <>
              {renderVariantCard(
                generatedVariants.variant_a,
                'A',
                selectedVariantId === generatedVariants.variant_a.id
              )}
              {renderVariantCard(
                generatedVariants.variant_b,
                'B',
                selectedVariantId === generatedVariants.variant_b.id
              )}
            </>
          ) : (
            <>
              {activeVariant === 'A' ? (
                renderVariantCard(
                  generatedVariants.variant_a,
                  'A',
                  selectedVariantId === generatedVariants.variant_a.id
                )
              ) : (
                renderVariantCard(
                  generatedVariants.variant_b,
                  'B',
                  selectedVariantId === generatedVariants.variant_b.id
                )
              )}
            </>
          )}
        </ScrollView>

        {/* Action Buttons */}
        <View style={styles.actions}>
          <Button
            mode="outlined"
            onPress={handleCopySelected}
            disabled={!selectedVariantId}
            icon={copied ? 'check' : 'content-copy'}
            style={styles.actionButton}
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>
          <Button
            mode="contained"
            onPress={handleMarkApplied}
            disabled={!selectedVariantId || markSentMutation.isPending}
            loading={markSentMutation.isPending}
            icon="check"
            style={[styles.actionButton, styles.primaryButton]}
          >
            Mark Applied
          </Button>
        </View>

        {/* Regenerate option */}
        <Button
          mode="text"
          onPress={handleGenerate}
          icon="refresh"
          style={styles.regenerateButton}
        >
          Generate New Variants
        </Button>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
  },
  subtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  closeButton: {
    padding: 4,
  },
  viewModeContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  segmentedButtons: {
    borderRadius: 8,
  },
  tabContainer: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 8,
    backgroundColor: '#f3f4f6',
    borderRadius: 8,
    padding: 4,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 6,
  },
  tabActive: {
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#6b7280',
  },
  tabTextActive: {
    color: '#111827',
  },
  variantsScroll: {
    flex: 1,
  },
  sideBySideContent: {
    paddingHorizontal: 12,
    gap: 12,
  },
  variantCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#e5e7eb',
    padding: 12,
    marginHorizontal: 4,
  },
  variantCardCompact: {
    width: SCREEN_WIDTH * 0.75,
    maxHeight: 400,
  },
  variantCardSelected: {
    borderColor: '#10b981',
    backgroundColor: '#f0fdf4',
  },
  variantHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  variantLabelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  variantBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  variantBadgeA: {
    backgroundColor: '#3b82f6',
  },
  variantBadgeB: {
    backgroundColor: '#8b5cf6',
  },
  variantBadgeText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
  variantName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  variantMeta: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 8,
  },
  metaChip: {
    backgroundColor: '#f3f4f6',
    height: 24,
  },
  metaChipText: {
    fontSize: 11,
    color: '#6b7280',
  },
  variantContent: {
    maxHeight: 300,
    backgroundColor: '#f9fafb',
    borderRadius: 8,
    padding: 12,
  },
  variantContentCompact: {
    maxHeight: 200,
  },
  variantText: {
    fontSize: 13,
    lineHeight: 20,
    color: '#374151',
  },
  selectButton: {
    marginTop: 12,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  actionButton: {
    flex: 1,
  },
  primaryButton: {
    backgroundColor: '#10b981',
  },
  regenerateButton: {
    alignSelf: 'center',
    marginBottom: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  loadingText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
    marginTop: 16,
  },
  loadingSubtext: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
    textAlign: 'center',
  },
  loadingProgress: {
    width: '80%',
    height: 4,
    marginTop: 24,
    borderRadius: 2,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#dc2626',
    marginTop: 16,
  },
  errorSubtext: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 24,
    marginBottom: 8,
  },
});

export default ProposalABTest;
