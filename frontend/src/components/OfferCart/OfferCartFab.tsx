import React, { useState } from 'react';
import { Fab, Badge, Tooltip } from '@mui/material';
import { ShoppingCart } from 'lucide-react';
import { useOfferCartStore } from '../../stores/offerCartStore';
import OfferCartDrawer from './OfferCartDrawer';

const OfferCartFab: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const itemsCount = useOfferCartStore((state) => state.items.length);

  return (
    <>
      <Tooltip title="Koszyk Ofertowy" placement="left">
        <Fab
          color="primary"
          aria-label="koszyk ofert"
          onClick={() => setDrawerOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 32,
            right: 32,
            zIndex: 1000,
          }}
        >
          <Badge badgeContent={itemsCount} color="error" overlap="circular">
            <ShoppingCart />
          </Badge>
        </Fab>
      </Tooltip>
      
      <OfferCartDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
};

export default OfferCartFab;
