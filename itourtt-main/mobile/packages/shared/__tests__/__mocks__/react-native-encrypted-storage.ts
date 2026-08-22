const store: Record<string, string> = {};
export default {
  setItem: jest.fn(async (key: string, value: string) => { store[key] = value; }),
  getItem: jest.fn(async (key: string) => store[key] || null),
  removeItem: jest.fn(async (key: string) => { delete store[key]; }),
  clear: jest.fn(async () => { Object.keys(store).forEach(k => delete store[k]); }),
};
