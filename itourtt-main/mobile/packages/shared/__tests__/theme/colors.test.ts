import { lightColors, darkColors, statusColors, statusColorsDark, serviceTypeColors } from '../../src/theme/colors';

describe('theme colors', () => {
  const requiredColorKeys = [
    'background',
    'foreground',
    'card',
    'cardForeground',
    'popover',
    'popoverForeground',
    'primary',
    'primaryForeground',
    'secondary',
    'secondaryForeground',
    'muted',
    'mutedForeground',
    'accent',
    'accentForeground',
    'destructive',
    'border',
    'input',
    'ring',
  ];

  describe('lightColors', () => {
    it('has all required color keys', () => {
      requiredColorKeys.forEach((key) => {
        expect(lightColors).toHaveProperty(key);
      });
    });

    it('has non-empty string values for all keys', () => {
      Object.values(lightColors).forEach((value) => {
        expect(typeof value).toBe('string');
        expect(value.length).toBeGreaterThan(0);
      });
    });

    it('has a white-ish background', () => {
      expect(lightColors.background).toBe('#FFFFFF');
    });

    it('has a dark foreground', () => {
      expect(lightColors.foreground).toBe('#09090B');
    });
  });

  describe('darkColors', () => {
    it('has all required color keys', () => {
      requiredColorKeys.forEach((key) => {
        expect(darkColors).toHaveProperty(key);
      });
    });

    it('has non-empty string values for all keys', () => {
      Object.values(darkColors).forEach((value) => {
        expect(typeof value).toBe('string');
        expect(value.length).toBeGreaterThan(0);
      });
    });

    it('has a dark background', () => {
      expect(darkColors.background).toBe('#09090B');
    });

    it('has a light foreground', () => {
      expect(darkColors.foreground).toBe('#FAFAFA');
    });
  });

  describe('light and dark color parity', () => {
    it('both theme objects have the same set of keys', () => {
      const lightKeys = Object.keys(lightColors).sort();
      const darkKeys = Object.keys(darkColors).sort();
      expect(lightKeys).toEqual(darkKeys);
    });
  });

  describe('statusColors', () => {
    const requiredStatuses = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'] as const;

    it('defines colors for all job statuses', () => {
      requiredStatuses.forEach((status) => {
        expect(statusColors).toHaveProperty(status);
      });
    });

    it('each status has bg, text, and border properties', () => {
      requiredStatuses.forEach((status) => {
        const color = statusColors[status];
        expect(color).toHaveProperty('bg');
        expect(color).toHaveProperty('text');
        expect(color).toHaveProperty('border');
        expect(typeof color.bg).toBe('string');
        expect(typeof color.text).toBe('string');
        expect(typeof color.border).toBe('string');
      });
    });

    it('light and dark status colors have the same statuses', () => {
      const lightStatuses = Object.keys(statusColors).sort();
      const darkStatuses = Object.keys(statusColorsDark).sort();
      expect(lightStatuses).toEqual(darkStatuses);
    });
  });

  describe('statusColorsDark', () => {
    const requiredStatuses = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'] as const;

    it('defines colors for all job statuses', () => {
      requiredStatuses.forEach((status) => {
        expect(statusColorsDark).toHaveProperty(status);
      });
    });

    it('each status has bg, text, and border properties', () => {
      requiredStatuses.forEach((status) => {
        const color = statusColorsDark[status];
        expect(color).toHaveProperty('bg');
        expect(color).toHaveProperty('text');
        expect(color).toHaveProperty('border');
      });
    });
  });

  describe('serviceTypeColors', () => {
    const requiredTypes = [
      'ARR',
      'DEP',
      'DAY_TOUR',
      'ONE_WAY_TRANSFER',
      'RETURN',
      'TWO_WAY_TRANSFER',
    ];

    it('defines colors for all service types', () => {
      requiredTypes.forEach((type) => {
        expect(serviceTypeColors).toHaveProperty(type);
      });
    });

    it('each service type has bg and text properties', () => {
      requiredTypes.forEach((type) => {
        const color = serviceTypeColors[type];
        expect(color).toHaveProperty('bg');
        expect(color).toHaveProperty('text');
        expect(typeof color.bg).toBe('string');
        expect(typeof color.text).toBe('string');
      });
    });
  });
});
