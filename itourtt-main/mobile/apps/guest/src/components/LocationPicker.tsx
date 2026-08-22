import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  FlatList,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import {
  publicApi,
  getColors,
  spacing,
  borderRadius,
  typography,
  type LocationTree,
  type ServiceType,
} from '@itour/shared';

// ─── Cached location tree ─────────────────────────────────────
let cachedTree: LocationTree | null = null;

async function getLocationTree(): Promise<LocationTree> {
  if (cachedTree) return cachedTree;
  const { data } = await publicApi.getLocations();
  const tree = (data as any)?.data ?? data;
  cachedTree = tree as LocationTree;
  return cachedTree;
}

// ─── Types ─────────────────────────────────────────────────────
type PickerLevel = 'country' | 'airport' | 'city' | 'zone' | 'hotel';

interface LocationPickerProps {
  serviceType: ServiceType | '';
  originAirportId: string;
  destinationAirportId: string;
  fromZoneId: string;
  toZoneId: string;
  hotelId: string;
  onChangeOriginAirport: (id: string, name: string) => void;
  onChangeDestinationAirport: (id: string, name: string) => void;
  onChangeFromZone: (id: string, name: string) => void;
  onChangeToZone: (id: string, name: string) => void;
  onChangeHotel: (id: string, name: string) => void;
}

interface PickItem {
  id: string;
  name: string;
  level: PickerLevel;
}

// ─── Component ─────────────────────────────────────────────────
export function LocationPicker({
  serviceType,
  originAirportId,
  destinationAirportId,
  fromZoneId,
  toZoneId,
  hotelId,
  onChangeOriginAirport,
  onChangeDestinationAirport,
  onChangeFromZone,
  onChangeToZone,
  onChangeHotel,
}: LocationPickerProps) {
  const colors = getColors('light');
  const [tree, setTree] = useState<LocationTree | null>(null);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [modalVisible, setModalVisible] = useState(false);
  const [modalTitle, setModalTitle] = useState('');
  const [modalItems, setModalItems] = useState<PickItem[]>([]);
  const [modalCallback, setModalCallback] = useState<((id: string, name: string) => void) | null>(null);

  // Display labels
  const [airportLabel, setAirportLabel] = useState('Select airport');
  const [zoneLabel, setZoneLabel] = useState('Select zone');
  const [hotelLabel, setHotelLabel] = useState('Select hotel (optional)');

  useEffect(() => {
    getLocationTree()
      .then(setTree)
      .finally(() => setLoading(false));
  }, []);

  // Flatten airports from tree
  const airports = useMemo(() => {
    if (!tree) return [];
    const list: PickItem[] = [];
    for (const country of tree.countries) {
      for (const airport of country.airports) {
        list.push({ id: airport.id, name: `${airport.name} (${airport.code})`, level: 'airport' });
      }
    }
    return list;
  }, [tree]);

  // Flatten zones from tree based on selected airport city hierarchy
  const zones = useMemo(() => {
    if (!tree) return [];
    const relevantAirportId = serviceType === 'ARR' ? originAirportId : destinationAirportId;
    if (!relevantAirportId) return [];
    const list: PickItem[] = [];
    for (const country of tree.countries) {
      for (const airport of country.airports) {
        if (airport.id === relevantAirportId) {
          for (const city of airport.cities) {
            for (const zone of city.zones) {
              list.push({ id: zone.id, name: `${city.name} - ${zone.name}`, level: 'zone' });
            }
          }
        }
      }
    }
    return list;
  }, [tree, serviceType, originAirportId, destinationAirportId]);

  // Flatten hotels from selected zone
  const hotels = useMemo(() => {
    if (!tree) return [];
    const zoneId = serviceType === 'ARR' ? toZoneId : fromZoneId;
    if (!zoneId) return [];
    const list: PickItem[] = [];
    for (const country of tree.countries) {
      for (const airport of country.airports) {
        for (const city of airport.cities) {
          for (const zone of city.zones) {
            if (zone.id === zoneId) {
              for (const hotel of zone.hotels) {
                list.push({ id: hotel.id, name: hotel.name, level: 'hotel' });
              }
            }
          }
        }
      }
    }
    return list;
  }, [tree, serviceType, toZoneId, fromZoneId]);

  const openPicker = useCallback(
    (title: string, items: PickItem[], cb: (id: string, name: string) => void) => {
      setModalTitle(title);
      setModalItems(items);
      setModalCallback(() => cb);
      setModalVisible(true);
    },
    [],
  );

  const handleSelect = useCallback(
    (item: PickItem) => {
      modalCallback?.(item.id, item.name);
      setModalVisible(false);
    },
    [modalCallback],
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator color="#1D4ED8" />
        <Text style={[typography.bodySm, { color: colors.mutedForeground, marginLeft: spacing[2] }]}>
          Loading locations...
        </Text>
      </View>
    );
  }

  // ARR: origin = airport, destination = zone/hotel
  // DEP: origin = zone/hotel, destination = airport
  const isArrival = serviceType === 'ARR';

  return (
    <View>
      {/* Airport Picker */}
      <Text style={[typography.label, { color: colors.foreground, marginBottom: spacing[1] }]}>
        {isArrival ? 'Arrival Airport' : 'Departure Airport'}
      </Text>
      <TouchableOpacity
        style={[styles.pickerButton, { borderColor: colors.input, backgroundColor: colors.background }]}
        onPress={() =>
          openPicker('Select Airport', airports, (id, name) => {
            if (isArrival) {
              onChangeOriginAirport(id, name);
            } else {
              onChangeDestinationAirport(id, name);
            }
            setAirportLabel(name);
            // Reset downstream
            setZoneLabel('Select zone');
            setHotelLabel('Select hotel (optional)');
          })
        }
      >
        <Text
          style={[
            typography.body,
            {
              color:
                (isArrival ? originAirportId : destinationAirportId)
                  ? colors.foreground
                  : colors.mutedForeground,
            },
          ]}
        >
          {airportLabel}
        </Text>
        <Text style={styles.chevron}>{'>'}</Text>
      </TouchableOpacity>

      {/* Zone Picker */}
      <Text
        style={[
          typography.label,
          { color: colors.foreground, marginBottom: spacing[1], marginTop: spacing[4] },
        ]}
      >
        {isArrival ? 'Destination Zone' : 'Pickup Zone'}
      </Text>
      <TouchableOpacity
        style={[styles.pickerButton, { borderColor: colors.input, backgroundColor: colors.background }]}
        onPress={() =>
          openPicker('Select Zone', zones, (id, name) => {
            if (isArrival) {
              onChangeToZone(id, name);
            } else {
              onChangeFromZone(id, name);
            }
            setZoneLabel(name);
            setHotelLabel('Select hotel (optional)');
          })
        }
        disabled={zones.length === 0}
      >
        <Text
          style={[
            typography.body,
            {
              color:
                (isArrival ? toZoneId : fromZoneId)
                  ? colors.foreground
                  : colors.mutedForeground,
            },
          ]}
        >
          {zoneLabel}
        </Text>
        <Text style={styles.chevron}>{'>'}</Text>
      </TouchableOpacity>

      {/* Hotel Picker */}
      <Text
        style={[
          typography.label,
          { color: colors.foreground, marginBottom: spacing[1], marginTop: spacing[4] },
        ]}
      >
        Hotel (optional)
      </Text>
      <TouchableOpacity
        style={[styles.pickerButton, { borderColor: colors.input, backgroundColor: colors.background }]}
        onPress={() =>
          openPicker('Select Hotel', hotels, (id, name) => {
            onChangeHotel(id, name);
            setHotelLabel(name);
          })
        }
        disabled={hotels.length === 0}
      >
        <Text
          style={[
            typography.body,
            { color: hotelId ? colors.foreground : colors.mutedForeground },
          ]}
        >
          {hotelLabel}
        </Text>
        <Text style={styles.chevron}>{'>'}</Text>
      </TouchableOpacity>

      {/* Selection Modal */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.background }]}>
            <View style={styles.modalHeader}>
              <Text style={[typography.h4, { color: colors.foreground }]}>{modalTitle}</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Text style={[typography.bodyMedium, { color: '#1D4ED8' }]}>Close</Text>
              </TouchableOpacity>
            </View>
            <FlatList
              data={modalItems}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[styles.modalItem, { borderBottomColor: colors.border }]}
                  onPress={() => handleSelect(item)}
                >
                  <Text style={[typography.body, { color: colors.foreground }]}>{item.name}</Text>
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View style={styles.emptyList}>
                  <Text style={[typography.bodySm, { color: colors.mutedForeground }]}>
                    No options available. Please select the previous field first.
                  </Text>
                </View>
              }
            />
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing[4],
  },
  pickerButton: {
    height: 48,
    borderWidth: 1,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing[3],
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  chevron: {
    fontSize: 16,
    color: '#71717A',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    maxHeight: '70%',
    borderTopLeftRadius: borderRadius['2xl'],
    borderTopRightRadius: borderRadius['2xl'],
    paddingBottom: spacing[8],
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: '#E4E4E7',
  },
  modalItem: {
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    borderBottomWidth: 1,
  },
  emptyList: {
    padding: spacing[6],
    alignItems: 'center',
  },
});
