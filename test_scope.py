def run():
    def build_reply():
        def extract():
            return clean("test")
        return extract()
    
    # build_reply is called BEFORE clean is defined? No, it's called at the end.
    
    def clean(s):
        return s.upper()

    print(build_reply())

run()
