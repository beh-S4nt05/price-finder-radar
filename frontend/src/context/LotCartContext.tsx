import React, { createContext, useContext, useState } from 'react';
import { LotEntry, ProductOfferDTO } from '../types/domain';

interface LotCartContextValue {
  entries: LotEntry[];
  isOpen: boolean;
  setOpen: (v: boolean) => void;
  addOffer: (offer: ProductOfferDTO) => void;
  updateQty: (offerId: string, qty: number) => void;
  removeOffer: (offerId: string) => void;
  clearLot: () => void;
}

const LotCartContext = createContext<LotCartContextValue | null>(null);

export const LotCartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [entries, setEntries] = useState<LotEntry[]>([]);
  const [isOpen, setOpen] = useState(false);

  const addOffer = (offer: ProductOfferDTO) => {
    setEntries((prev) => {
      const idx = prev.findIndex((e) => e.offer.offer_id === offer.offer_id);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = { ...copy[idx], quantity: copy[idx].quantity + 1 };
        return copy;
      }
      return [...prev, { offer, quantity: 1 }];
    });
  };

  const updateQty = (offerId: string, qty: number) => {
    if (qty <= 0) {
      setEntries((prev) => prev.filter((e) => e.offer.offer_id !== offerId));
      return;
    }
    setEntries((prev) =>
      prev.map((e) => (e.offer.offer_id === offerId ? { ...e, quantity: qty } : e))
    );
  };

  const removeOffer = (offerId: string) => {
    setEntries((prev) => prev.filter((e) => e.offer.offer_id !== offerId));
  };

  const clearLot = () => setEntries([]);

  return (
    <LotCartContext.Provider
      value={{ entries, isOpen, setOpen, addOffer, updateQty, removeOffer, clearLot }}
    >
      {children}
    </LotCartContext.Provider>
  );
};

export const useLotCart = () => {
  const ctx = useContext(LotCartContext);
  if (!ctx) throw new Error('useLotCart must be used inside LotCartProvider');
  return ctx;
};
