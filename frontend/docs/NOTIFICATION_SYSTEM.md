# Notification System Documentation

## Overview

The application now uses an industry-standard notification system with **Toast notifications** and **Modal dialogs** instead of browser native `alert()` and `confirm()` popups.

## Components

### 1. Toast Notifications

**Location**: `frontend/src/components/common/Toast.tsx`

Toast notifications are non-blocking, auto-dismissing messages that appear in the top-right corner of the screen.

**Features**:
- 4 types: `success`, `error`, `warning`, `info`
- Auto-dismiss after configurable duration (default: 5 seconds)
- Manual dismiss with close button
- Smooth slide-in/slide-out animations
- Color-coded with appropriate icons
- Supports multi-line messages

**Usage**:
```tsx
import { useNotification } from '../contexts/NotificationContext';

const MyComponent = () => {
  const { showSuccess, showError, showWarning, showInfo } = useNotification();

  // Success notification
  showSuccess('Operation Successful', 'Your changes have been saved');

  // Error notification
  showError('Operation Failed', 'Please try again later');

  // Warning notification (with custom duration)
  showWarning('Manual Configuration Required', 'See details below', 10000);

  // Info notification
  showInfo('New Feature', 'Check out our latest updates');
};
```

### 2. Modal Dialogs

**Location**: `frontend/src/components/common/Modal.tsx`

Modal dialogs are blocking overlays used for confirmations and important alerts.

**Features**:
- Backdrop overlay with click-to-close
- Escape key to close
- Customizable buttons (confirm/cancel)
- Two variants: `default` and `danger`
- Prevents body scroll when open
- Accessible (ARIA attributes)

**Usage**:
```tsx
import { useNotification } from '../contexts/NotificationContext';

const MyComponent = () => {
  const { showConfirm } = useNotification();

  // Confirmation dialog (default variant)
  const handleAction = () => {
    showConfirm(
      'Confirm Action',
      'Are you sure you want to proceed?',
      () => {
        // Action to perform on confirm
        console.log('Confirmed!');
      }
    );
  };

  // Danger confirmation (red button)
  const handleDelete = () => {
    showConfirm(
      'Delete Item',
      'This action cannot be undone.',
      () => {
        // Delete action
        console.log('Deleted!');
      },
      'danger'
    );
  };
};
```

## Architecture

### NotificationContext

**Location**: `frontend/src/contexts/NotificationContext.tsx`

Provides notification functionality throughout the application via React Context.

**Provider Setup** (in `App.tsx`):
```tsx
import { NotificationProvider } from './contexts/NotificationContext';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NotificationProvider>
        {/* Your app content */}
      </NotificationProvider>
    </QueryClientProvider>
  );
}
```

### Custom Hooks

#### useToast
**Location**: `frontend/src/hooks/useToast.ts`

Manages toast notification state and provides methods to add/remove toasts.

#### useModal
**Location**: `frontend/src/hooks/useModal.ts`

Manages modal dialog state and provides methods to open/close modals.

## Migration from Browser Popups

### Before (Browser Native)
```tsx
// Alert
alert('Sync completed: 8 APIs discovered');

// Confirm
if (window.confirm('Delete this gateway?')) {
  deleteGateway();
}
```

### After (Industry Standard)
```tsx
import { useNotification } from '../contexts/NotificationContext';

const MyComponent = () => {
  const { showSuccess, showConfirm } = useNotification();

  // Toast notification
  showSuccess('Sync Completed', '8 APIs discovered');

  // Modal confirmation
  showConfirm(
    'Delete Gateway',
    'Are you sure you want to delete this gateway?',
    () => deleteGateway(),
    'danger'
  );
};
```

## Replaced Popups

### Gateways Page (`frontend/src/pages/Gateways.tsx`)
- ✅ Gateway sync success/failure → Toast notifications
- ✅ Bulk sync failure → Toast notification
- ✅ Gateway connect/disconnect → Toast notifications
- ✅ Gateway delete confirmation → Modal dialog (danger variant)
- ✅ Gateway disconnect confirmation → Modal dialog
- ✅ No gateway selected warning → Toast notification

### Optimization Page (`frontend/src/pages/Optimization.tsx`)
- ✅ Policy applied success → Toast notification
- ✅ Manual configuration required → Warning toast (10s duration)
- ✅ Policy removed success → Toast notification
- ✅ Validation success/failure → Toast notifications
- ✅ Remove policy confirmation → Modal dialog
- ✅ Apply/remove/validate errors → Error toast notifications

### Query Page (`frontend/src/pages/Query.tsx`)
- ✅ Clear conversation confirmation → Modal dialog
- ✅ New conversation confirmation → Modal dialog

## Design Decisions

### Why Toast Notifications?
1. **Non-blocking**: Users can continue working while viewing notifications
2. **Auto-dismiss**: Reduces cognitive load by automatically clearing
3. **Stackable**: Multiple notifications can be shown simultaneously
4. **Professional**: Industry-standard UX pattern used by major applications

### Why Modal Dialogs?
1. **Blocking**: Forces user attention for critical decisions
2. **Accessible**: Keyboard navigation and screen reader support
3. **Customizable**: Different variants for different severity levels
4. **Consistent**: Unified look and feel across the application

### Color Coding
- **Green** (Success): Positive outcomes, successful operations
- **Red** (Error): Failures, errors, critical issues
- **Yellow** (Warning): Cautions, manual actions required
- **Blue** (Info): Informational messages, tips

## Best Practices

### When to Use Toast Notifications
- Operation success/failure feedback
- Non-critical warnings
- Informational messages
- Background process updates

### When to Use Modal Dialogs
- Destructive actions (delete, remove)
- Important confirmations
- Actions that cannot be undone
- Critical warnings requiring acknowledgment

### Duration Guidelines
- **Success**: 5 seconds (default)
- **Error**: 5 seconds (default)
- **Warning**: 8-10 seconds (more time to read)
- **Info**: 5 seconds (default)

### Message Guidelines
- **Title**: Short, action-oriented (e.g., "Sync Completed")
- **Message**: Provide context and details (e.g., "8 APIs discovered")
- **Avoid**: Technical jargon, error codes without explanation
- **Include**: Actionable information when possible

## Accessibility

### Toast Notifications
- `role="alert"` for screen readers
- `aria-live="polite"` for non-intrusive announcements
- Keyboard dismissible (focus trap not needed)

### Modal Dialogs
- `role="dialog"` and `aria-modal="true"`
- `aria-labelledby` for title association
- Escape key to close
- Focus trap within modal
- Body scroll prevention

## Future Enhancements

Potential improvements for the notification system:

1. **Toast Queue Management**: Limit simultaneous toasts (e.g., max 3)
2. **Action Buttons**: Add action buttons to toasts (e.g., "Undo", "View Details")
3. **Persistent Toasts**: Option for toasts that don't auto-dismiss
4. **Sound Effects**: Optional audio feedback for notifications
5. **Position Options**: Allow toasts in different screen positions
6. **Animation Variants**: Different animation styles (fade, slide, bounce)
7. **Toast History**: View dismissed notifications in a history panel
8. **Notification Preferences**: User settings for notification behavior

## Testing

To test the notification system:

1. **Gateway Sync**: Navigate to Gateways page and sync a gateway
2. **Gateway Delete**: Try to delete a gateway (modal should appear)
3. **Policy Apply**: Apply an optimization recommendation
4. **Policy Remove**: Remove a policy (modal should appear)
5. **Query Clear**: Clear conversation history (modal should appear)

Expected behavior:
- Toasts appear in top-right corner
- Toasts auto-dismiss after specified duration
- Modals block interaction with background
- Modals close on backdrop click or Escape key
- Multiple toasts stack vertically

## Troubleshooting

### Toasts Not Appearing
- Verify `NotificationProvider` wraps your app in `App.tsx`
- Check browser console for errors
- Ensure `useNotification` is called within a component

### Modals Not Blocking
- Check z-index values (modal should be z-50)
- Verify backdrop overlay is rendering
- Check for CSS conflicts

### TypeScript Errors
- Ensure all notification methods are properly typed
- Import types from `NotificationContext`
- Check component prop types match expected values

## Related Files

- `frontend/src/components/common/Toast.tsx` - Toast component
- `frontend/src/components/common/ToastContainer.tsx` - Toast container
- `frontend/src/components/common/Modal.tsx` - Modal component
- `frontend/src/contexts/NotificationContext.tsx` - Context provider
- `frontend/src/hooks/useToast.ts` - Toast hook
- `frontend/src/hooks/useModal.ts` - Modal hook
- `frontend/src/components/common/index.ts` - Component exports