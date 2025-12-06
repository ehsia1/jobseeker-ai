'use client';

import { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Building,
  DollarSign,
  MapPin,
  ExternalLink,
  StickyNote,
  GripVertical,
  Star,
  Clock,
  Loader2,
  Check,
} from 'lucide-react';
import { toast } from 'sonner';
import type { JobMatch, JobMatchStatus } from '@/lib/types';
import { formatDistanceToNow } from 'date-fns';

interface KanbanColumn {
  id: JobMatchStatus;
  title: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

const KANBAN_COLUMNS: KanbanColumn[] = [
  {
    id: 'new',
    title: 'New Matches',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  {
    id: 'saved',
    title: 'Saved',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
  },
  {
    id: 'applied',
    title: 'Applied',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
  {
    id: 'interviewing',
    title: 'Interviewing',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
  },
  {
    id: 'hired',
    title: 'Hired',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
  },
  {
    id: 'rejected',
    title: 'Rejected',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
  },
];

// Map legacy statuses to new ones
function normalizeStatus(status: JobMatchStatus): JobMatchStatus {
  if (status === 'pending' || status === 'viewed') {
    return 'new';
  }
  return status;
}

interface KanbanCardProps {
  match: JobMatch;
  onStatusChange: (matchId: string, status: JobMatchStatus) => Promise<void>;
  onNotesChange: (matchId: string, notes: string) => Promise<void>;
}

function KanbanCard({ match, onStatusChange, onNotesChange }: KanbanCardProps) {
  const [notesOpen, setNotesOpen] = useState(false);
  const [notes, setNotes] = useState(match.client_notes || '');
  const [savingNotes, setSavingNotes] = useState(false);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: match.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const formatRate = (min?: number, max?: number, type?: string) => {
    if (!min && !max) return null;
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    });
    const suffix = type === 'hourly' ? '/hr' : type === 'annual' ? '/yr' : '';
    if (min && max) return `${formatter.format(min)}-${formatter.format(max)}${suffix}`;
    if (min) return `${formatter.format(min)}+${suffix}`;
    return null;
  };

  const handleSaveNotes = async () => {
    setSavingNotes(true);
    try {
      await onNotesChange(match.id, notes);
      toast.success('Notes saved');
      setNotesOpen(false);
    } catch {
      toast.error('Failed to save notes');
    } finally {
      setSavingNotes(false);
    }
  };

  const scoreColor = match.total_score >= 80
    ? 'text-green-600 bg-green-50'
    : match.total_score >= 60
      ? 'text-blue-600 bg-blue-50'
      : match.total_score >= 40
        ? 'text-yellow-600 bg-yellow-50'
        : 'text-red-600 bg-red-50';

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-white dark:bg-gray-800 rounded-lg border shadow-sm hover:shadow-md transition-shadow p-3 space-y-2"
    >
      {/* Drag Handle & Title */}
      <div className="flex items-start gap-2">
        <button
          {...attributes}
          {...listeners}
          className="mt-1 p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 cursor-grab active:cursor-grabbing"
        >
          <GripVertical className="w-4 h-4 text-gray-400" />
        </button>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm leading-tight truncate">
            {match.job.title}
          </h4>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-0.5">
            <Building className="w-3 h-3" />
            <span className="truncate">{match.job.company}</span>
          </div>
        </div>
        <Badge variant="secondary" className={`text-xs shrink-0 ${scoreColor}`}>
          <Star className="w-3 h-3 mr-0.5" />
          {Math.round(match.total_score)}%
        </Badge>
      </div>

      {/* Meta Info */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {match.job.location && (
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {match.job.remote ? 'Remote' : match.job.location}
          </span>
        )}
        {formatRate(match.job.rate_min, match.job.rate_max, match.job.rate_type) && (
          <span className="flex items-center gap-1">
            <DollarSign className="w-3 h-3" />
            {formatRate(match.job.rate_min, match.job.rate_max, match.job.rate_type)}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatDistanceToNow(new Date(match.created_at), { addSuffix: true })}
        </span>
      </div>

      {/* Skills Preview */}
      {match.job.skills && match.job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {match.job.skills.slice(0, 3).map((skill) => (
            <Badge key={skill} variant="outline" className="text-xs py-0 px-1.5">
              {skill}
            </Badge>
          ))}
          {match.job.skills.length > 3 && (
            <Badge variant="outline" className="text-xs py-0 px-1.5">
              +{match.job.skills.length - 3}
            </Badge>
          )}
        </div>
      )}

      {/* Notes Indicator */}
      {match.client_notes && (
        <div className="text-xs text-muted-foreground bg-yellow-50 dark:bg-yellow-900/20 rounded px-2 py-1 line-clamp-1">
          <StickyNote className="w-3 h-3 inline mr-1 text-yellow-600" />
          {match.client_notes}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1 border-t">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                onClick={() => window.open(match.job.url, '_blank')}
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>View job posting</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <Dialog open={notesOpen} onOpenChange={setNotesOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 px-2">
              <StickyNote className="w-3.5 h-3.5" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Notes for {match.job.title}</DialogTitle>
              <DialogDescription>
                Add notes about this opportunity, contact info, or reminders.
              </DialogDescription>
            </DialogHeader>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add your notes here..."
              className="min-h-[120px]"
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setNotesOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveNotes} disabled={savingNotes}>
                {savingNotes ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Check className="w-4 h-4 mr-2" />
                )}
                Save Notes
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

interface KanbanColumnProps {
  column: KanbanColumn;
  matches: JobMatch[];
  onStatusChange: (matchId: string, status: JobMatchStatus) => Promise<void>;
  onNotesChange: (matchId: string, notes: string) => Promise<void>;
}

function KanbanColumnComponent({
  column,
  matches,
  onStatusChange,
  onNotesChange,
}: KanbanColumnProps) {
  return (
    <div className={`flex flex-col min-w-[280px] max-w-[320px] rounded-lg ${column.bgColor} border ${column.borderColor}`}>
      <div className="p-3 border-b border-inherit">
        <div className="flex items-center justify-between">
          <h3 className={`font-semibold ${column.color}`}>{column.title}</h3>
          <Badge variant="secondary" className="text-xs">
            {matches.length}
          </Badge>
        </div>
      </div>
      <div className="flex-1 p-2 space-y-2 overflow-y-auto min-h-[200px] max-h-[calc(100vh-300px)]">
        <SortableContext
          items={matches.map((m) => m.id)}
          strategy={verticalListSortingStrategy}
        >
          {matches.map((match) => (
            <KanbanCard
              key={match.id}
              match={match}
              onStatusChange={onStatusChange}
              onNotesChange={onNotesChange}
            />
          ))}
        </SortableContext>
        {matches.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-8">
            No matches
          </div>
        )}
      </div>
    </div>
  );
}

interface KanbanBoardProps {
  matches: JobMatch[];
  onStatusChange: (matchId: string, status: JobMatchStatus) => Promise<void>;
  onNotesChange: (matchId: string, notes: string) => Promise<void>;
  loading?: boolean;
}

export default function KanbanBoard({
  matches,
  onStatusChange,
  onNotesChange,
  loading,
}: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Group matches by normalized status
  const matchesByColumn = useMemo(() => {
    const grouped: Record<JobMatchStatus, JobMatch[]> = {
      new: [],
      saved: [],
      applied: [],
      interviewing: [],
      hired: [],
      rejected: [],
      pending: [],
      viewed: [],
    };

    matches.forEach((match) => {
      const normalizedStatus = normalizeStatus(match.status);
      grouped[normalizedStatus].push(match);
    });

    return grouped;
  }, [matches]);

  const activeMatch = useMemo(
    () => matches.find((m) => m.id === activeId),
    [matches, activeId]
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: DragOverEvent) => {
    // Could be used for visual feedback during drag
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeMatchId = active.id as string;
    const overMatchId = over.id as string;

    // Find which column the item was dropped into
    const targetColumn = KANBAN_COLUMNS.find((col) =>
      matchesByColumn[col.id].some((m) => m.id === overMatchId)
    );

    // If dropped on empty column, check if over.id is a column id
    const droppedOnColumn = KANBAN_COLUMNS.find((col) => col.id === overMatchId);

    const newStatus = targetColumn?.id || droppedOnColumn?.id;

    if (newStatus) {
      const activeMatch = matches.find((m) => m.id === activeMatchId);
      if (activeMatch && normalizeStatus(activeMatch.status) !== newStatus) {
        try {
          await onStatusChange(activeMatchId, newStatus);
          toast.success(`Moved to ${KANBAN_COLUMNS.find((c) => c.id === newStatus)?.title}`);
        } catch {
          toast.error('Failed to update status');
        }
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {KANBAN_COLUMNS.map((column) => (
          <KanbanColumnComponent
            key={column.id}
            column={column}
            matches={matchesByColumn[column.id]}
            onStatusChange={onStatusChange}
            onNotesChange={onNotesChange}
          />
        ))}
      </div>

      <DragOverlay>
        {activeMatch && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border shadow-lg p-3 w-[280px] opacity-90">
            <h4 className="font-medium text-sm">{activeMatch.job.title}</h4>
            <p className="text-xs text-muted-foreground">{activeMatch.job.company}</p>
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
