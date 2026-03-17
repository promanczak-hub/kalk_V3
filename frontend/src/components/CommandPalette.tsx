import { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogContent, 
  TextField, 
  List, 
  ListItem, 
  ListItemButton, 
  ListItemText, 
  ListItemIcon, 
  Typography, 
  Box, 
  InputAdornment,
  Chip
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import SettingsIcon from '@mui/icons-material/Settings';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';

interface Command {
  id: string;
  name: string;
  icon: React.ReactNode;
  action: () => void;
  shortcut?: string;
}

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleClose = () => {
    setOpen(false);
    setSearch('');
  };

  const dispatchTabStatus = (index: number) => {
     window.dispatchEvent(
      new CustomEvent('switchTab', {
        detail: { tabIndex: index },
      })
    );
  }

  const commands: Command[] = [
    {
      id: 'vertex',
      name: 'Przejdź do: Vertex Extractor',
      icon: <PictureAsPdfIcon color="primary" />,
      action: () => dispatchTabStatus(0),
      shortcut: 'T1'
    },
    {
      id: 'control',
      name: 'Przejdź do: Control Center',
      icon: <SettingsIcon color="primary" />,
      action: () => dispatchTabStatus(1),
      shortcut: 'T2'
    },

  ];

  const filteredCommands = commands.filter(c => c.name.toLowerCase().includes(search.toLowerCase()));

  // Allow enter to select first option
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && filteredCommands.length > 0) {
      filteredCommands[0].action();
      handleClose();
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      maxWidth="sm" 
      fullWidth 
      PaperProps={{ 
        sx: { 
          borderRadius: 3, 
          top: '-15%', 
          boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
          backgroundImage: 'none'
        } 
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        <TextField
          autoFocus
          fullWidth
          placeholder="Szukaj komendy... (Naciśnij Enter)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleInputKeyDown}
          variant="outlined"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 0,
              '& fieldset': { border: 'none', borderBottom: '1px solid #e0e0e0' },
            },
            '& input': {
              p: 2.5,
              fontSize: '1.1rem'
            }
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start" sx={{ pl: 1 }}>
                <SearchIcon color="action" />
              </InputAdornment>
            ),
          }}
        />
        <List sx={{ pb: 1, maxHeight: 300, overflow: 'auto' }}>
          {filteredCommands.length > 0 ? (
            filteredCommands.map((command, idx) => (
              <ListItem key={command.id} disablePadding>
                <ListItemButton 
                  onClick={() => {
                    command.action();
                    handleClose();
                  }}
                  selected={idx === 0 && search.length > 0} // Highlight first item when searching
                  sx={{ py: 1.5, px: 3 }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {command.icon}
                  </ListItemIcon>
                  <ListItemText 
                    primary={command.name} 
                    primaryTypographyProps={{ fontWeight: 500 }} 
                  />
                  {command.shortcut && (
                    <Chip 
                      label={command.shortcut} 
                      size="small" 
                      sx={{ 
                        height: 20, 
                        fontSize: '0.7rem', 
                        borderRadius: 1,
                        bgcolor: 'rgba(0,0,0,0.05)'
                      }} 
                    />
                  )}
                </ListItemButton>
              </ListItem>
            ))
          ) : (
             <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="text.secondary">Nie znaleziono komendy.</Typography>
             </Box>
          )}
        </List>
        <Box sx={{ px: 3, py: 1.5, borderTop: '1px solid #f0f0f0', bgcolor: '#fafafa', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              Nawigacja za pomocą klawiatury jest dostępna.
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', gap: 1 }}>
              <kbd style={{ padding: '2px 6px', backgroundColor: '#eee', borderRadius: '4px' }}>ESC</kbd> zamknij
            </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
