import React from 'react';
import { View, ActivityIndicator, StyleSheet, Dimensions } from 'react-native';
import { Text, ProgressBar } from 'react-native-paper';

interface AgentLoadingStateProps {
  color: string;
  progress: number;
  statusText: string;
}

const PROGRESS_BAR_WIDTH = Dimensions.get('window').width * 0.65;

export function AgentLoadingState({ color, progress, statusText }: AgentLoadingStateProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color={color} />
      <ProgressBar
        progress={progress}
        color={color}
        style={styles.progressBar}
      />
      <Text variant="bodySmall" style={[styles.statusText, { color }]} numberOfLines={2}>
        {statusText}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressBar: {
    width: PROGRESS_BAR_WIDTH,
    height: 4,
    borderRadius: 2,
    marginTop: 16,
    marginBottom: 16,
  },
  statusText: {
    textAlign: 'center',
    lineHeight: 18,
  },
});
