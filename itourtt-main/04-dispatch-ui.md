# iTour Transport & Traffic – Dispatch UI (Excel-like)

## Design Principles
- Grid-based layout
- Keyboard navigation
- Inline editing
- Auto-save
- Real-time validation

## Layout

Date Selector + Filters

ARRIVALS (Left Grid) | DEPARTURES (Right Grid)

Columns:
- Time
- Flight
- Pax
- Hotel / Zone
- Vehicle
- Driver
- Rep
- Status

## Interaction
- Enter to edit cell
- Arrow keys to move
- Dropdowns behave like Excel validation lists
- Ctrl + S saves all

## Color Codes
- Red: Unassigned
- Yellow: Partially assigned
- Green: Fully assigned

## Components
- DispatchPage
- DateToolbar
- ArrivalGrid
- DepartureGrid
- SummaryFooter