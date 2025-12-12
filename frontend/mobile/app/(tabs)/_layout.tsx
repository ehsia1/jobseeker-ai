import React from 'react';
import FontAwesome from '@expo/vector-icons/FontAwesome';
import { Tabs } from 'expo-router';

import { useColorScheme } from '@/components/useColorScheme';

function TabBarIcon(props: {
  name: React.ComponentProps<typeof FontAwesome>['name'];
  color: string;
}) {
  return <FontAwesome size={24} style={{ marginBottom: -3 }} {...props} />;
}

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#3b82f6',
        tabBarInactiveTintColor: colorScheme === 'dark' ? '#9ca3af' : '#6b7280',
        headerShown: true,
        headerStyle: {
          backgroundColor: colorScheme === 'dark' ? '#1f2937' : '#fff',
        },
        headerTintColor: colorScheme === 'dark' ? '#fff' : '#111827',
        tabBarStyle: {
          backgroundColor: colorScheme === 'dark' ? '#1f2937' : '#fff',
          borderTopColor: colorScheme === 'dark' ? '#374151' : '#e5e7eb',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Jobs',
          tabBarIcon: ({ color }) => <TabBarIcon name="briefcase" color={color} />,
        }}
      />
      <Tabs.Screen
        name="matches"
        options={{
          title: 'Matches',
          tabBarIcon: ({ color }) => <TabBarIcon name="star" color={color} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => <TabBarIcon name="user" color={color} />,
        }}
      />
    </Tabs>
  );
}
