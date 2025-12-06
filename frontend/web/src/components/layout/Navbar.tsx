'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bell, Search, User, Settings, LogOut, Briefcase, CreditCard, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useCurrentUser, useNotifications } from '@/hooks/useAPI';
import { apiClient } from '@/lib/api/client';

export default function Navbar() {
  const router = useRouter();
  const { user } = useCurrentUser();
  const { unreadCount } = useNotifications(1, 5);

  const handleLogout = () => {
    apiClient.clearAuthToken();
    router.push('/login');
  };

  const getInitials = (name?: string) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 max-w-7xl mx-auto">
        {/* Logo */}
        <div className="mr-4">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <Briefcase className="h-6 w-6 text-primary" />
            <span className="font-bold text-lg">JobSeeker AI</span>
          </Link>
        </div>

        {/* Navigation Links */}
        <div className="flex items-center space-x-6 text-sm font-medium mr-auto">
          <Link
            href="/dashboard"
            className="transition-colors hover:text-foreground/80 text-foreground/60"
          >
            Dashboard
          </Link>
          <Link
            href="/jobs"
            className="transition-colors hover:text-foreground/80 text-foreground/60"
          >
            Jobs
          </Link>
          <Link
            href="/matches"
            className="transition-colors hover:text-foreground/80 text-foreground/60"
          >
            Matches
          </Link>
          <Link
            href="/search"
            className="transition-colors hover:text-foreground/80 text-foreground/60"
          >
            Search
          </Link>
          <Link
            href="/pricing"
            className="transition-colors hover:text-foreground/80 text-foreground/60 flex items-center gap-1"
          >
            <Sparkles className="h-3 w-3" />
            Pricing
          </Link>
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center space-x-4">
          {/* Search Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/search')}
          >
            <Search className="h-4 w-4" />
            <span className="sr-only">Search jobs</span>
          </Button>

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <Badge
                    variant="destructive"
                    className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </Badge>
                )}
                <span className="sr-only">View notifications</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>Notifications</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {unreadCount === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No new notifications
                </div>
              ) : (
                <>
                  <div className="p-2">
                    <div className="text-sm text-muted-foreground">
                      {unreadCount} unread notifications
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/notifications" className="w-full">
                      View all notifications
                    </Link>
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage src="#" alt={user?.full_name || user?.email} />
                  <AvatarFallback>
                    {getInitials(user?.full_name)}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user?.full_name || 'User'}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/profile" className="flex items-center">
                  <User className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/settings" className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/pricing" className="flex items-center">
                  <CreditCard className="mr-2 h-4 w-4" />
                  <span>Subscription</span>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </nav>
  );
}