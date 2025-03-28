from make_abridged_ipo_financial import make_abridged_financial
from ipo_g_pdf_financial import extract_pdf_financial


def main():
    ##  financial versions of pdf
    stock_name = "panda"
    pdf_name = f"{stock_name}.pdf"
    financial_name = f"{stock_name}_financial.pdf"

    make_abridged_financial(pdf_name)

    # extrac data
    extract_pdf_financial(financial_name)



if __name__ == '__main__':
    main()